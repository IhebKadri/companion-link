import 'dart:async';
import 'dart:io';

import 'package:multicast_dns/multicast_dns.dart';

import '../models/discovered_device.dart';

class DiscoveryService {
  static const String _serviceType = '_companionlink._tcp.local';
  static const Duration _defaultTimeout = Duration(seconds: 5);

  Future<List<DiscoveredDevice>> scan({Duration? timeout}) async {
    final client = MDnsClient();
    final devices = <String, DiscoveredDevice>{};

    try {
      await client.start();
      final scanWindow = timeout ?? _defaultTimeout;

      await for (final ptr in client
          .lookup<PtrResourceRecord>(
              ResourceRecordQuery.serverPointer(_serviceType))
          .timeout(scanWindow, onTimeout: (sink) => sink.close())) {
        final device = await _resolveDevice(client, ptr.domainName);
        if (device != null) devices[device.deviceId] = device;
      }
    } on SocketException {
      // mDNS unavailable on this network/platform — return what we have.
    } finally {
      client.stop();
    }

    return devices.values.toList(growable: false);
  }

  Future<DiscoveredDevice?> _resolveDevice(
    MDnsClient client,
    String domainName,
  ) async {
    const lookupTimeout = Duration(seconds: 2);

    final srvRecords = await client
        .lookup<SrvResourceRecord>(ResourceRecordQuery.service(domainName))
        .timeout(lookupTimeout, onTimeout: (sink) => sink.close())
        .toList();
    if (srvRecords.isEmpty) return null;
    final srv = srvRecords.first;

    final ipRecords = await client
        .lookup<IPAddressResourceRecord>(
            ResourceRecordQuery.addressIPv4(srv.target))
        .timeout(lookupTimeout, onTimeout: (sink) => sink.close())
        .toList();
    if (ipRecords.isEmpty) return null;

    final txtRecords = await client
        .lookup<TxtResourceRecord>(ResourceRecordQuery.text(domainName))
        .timeout(lookupTimeout, onTimeout: (sink) => sink.close())
        .toList();
    final props = _parseTxtRecords(txtRecords);
    final deviceId = props['device_id'];
    if (deviceId == null) return null;

    return DiscoveredDevice(
      deviceId: deviceId,
      deviceName: props['device_name'] ?? srv.target,
      host: ipRecords.first.address.address,
      port: srv.port,
      protocolVersion: props['protocol_version'] ?? 'unknown',
    );
  }

  Map<String, String> _parseTxtRecords(List<TxtResourceRecord> records) {
    final result = <String, String>{};
    for (final record in records) {
      for (final entry in record.text.split('\n')) {
        final idx = entry.indexOf('=');
        if (idx == -1) continue;
        result[entry.substring(0, idx)] = entry.substring(idx + 1);
      }
    }
    return result;
  }
}