/// Metadata about a Companion Link PC daemon discovered on the local network.
class DiscoveredDevice {
  const DiscoveredDevice({
    required this.deviceId,
    required this.deviceName,
    required this.host,
    required this.port,
    required this.protocolVersion,
  });

  final String deviceId;
  final String deviceName;
  final String host;
  final int port;
  final String protocolVersion;

  @override
  String toString() =>
      'DiscoveredDevice($deviceName, $deviceId, $host:$port)';
}