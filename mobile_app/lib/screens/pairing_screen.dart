import 'package:flutter/material.dart';

import '../models/discovered_device.dart';
import '../services/discovery_service.dart';
import '../services/pairing_client.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _discoveryService = DiscoveryService();
  final _pairingClient = PairingClient();
  final _codeController = TextEditingController();
  final _deviceNameController = TextEditingController(text: 'My Phone');

  List<DiscoveredDevice> _devices = [];
  DiscoveredDevice? _selectedDevice;
  bool _isScanning = false;
  bool _isPairing = false;
  String? _statusMessage;
  bool _statusIsError = false;

  Future<void> _scan() async {
    setState(() {
      _isScanning = true;
      _statusMessage = null;
    });
    try {
      final devices = await _discoveryService.scan();
      setState(() => _devices = devices);
    } catch (e) {
      setState(() {
        _statusMessage = 'Scan failed: $e';
        _statusIsError = true;
      });
    } finally {
      setState(() => _isScanning = false);
    }
  }

  Future<void> _pair() async {
    final device = _selectedDevice;
    if (device == null) {
      setState(() {
        _statusMessage = 'Select a PC first';
        _statusIsError = true;
      });
      return;
    }

    setState(() {
      _isPairing = true;
      _statusMessage = null;
    });

    try {
      await _pairingClient.pair(
        pcHost: device.host,
        code: _codeController.text.trim(),
        deviceName: _deviceNameController.text.trim(),
      );
      setState(() {
        _statusMessage = 'Paired successfully with ${device.deviceName}';
        _statusIsError = false;
      });
    } on PairingException catch (e) {
      setState(() {
        _statusMessage = e.message;
        _statusIsError = true;
      });
    } finally {
      setState(() => _isPairing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pair with PC')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ElevatedButton(
              onPressed: _isScanning ? null : _scan,
              child: Text(_isScanning ? 'Scanning...' : 'Scan for PC'),
            ),
            const SizedBox(height: 12),
            if (_devices.isNotEmpty)
              DropdownButton<DiscoveredDevice>(
                isExpanded: true,
                hint: const Text('Select a PC'),
                value: _selectedDevice,
                items: _devices
                    .map((d) => DropdownMenuItem(value: d, child: Text(d.deviceName)))
                    .toList(),
                onChanged: (d) => setState(() => _selectedDevice = d),
              ),
            const SizedBox(height: 16),
            TextField(
              controller: _deviceNameController,
              decoration: const InputDecoration(labelText: 'This device\'s name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _codeController,
              decoration: const InputDecoration(labelText: 'Pairing code from PC'),
              keyboardType: TextInputType.number,
              maxLength: 6,
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _isPairing ? null : _pair,
              child: Text(_isPairing ? 'Pairing...' : 'Pair'),
            ),
            const SizedBox(height: 16),
            if (_statusMessage != null)
              Text(
                _statusMessage!,
                style: TextStyle(color: _statusIsError ? Colors.red : Colors.green),
              ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _codeController.dispose();
    _deviceNameController.dispose();
    super.dispose();
  }
}