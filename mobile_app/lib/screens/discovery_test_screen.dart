import 'package:flutter/material.dart';

import '../models/discovered_device.dart';
import '../services/discovery_service.dart';

class DiscoveryTestScreen extends StatefulWidget {
  const DiscoveryTestScreen({super.key});

  @override
  State<DiscoveryTestScreen> createState() => _DiscoveryTestScreenState();
}

class _DiscoveryTestScreenState extends State<DiscoveryTestScreen> {
  final _discoveryService = DiscoveryService();
  List<DiscoveredDevice> _devices = [];
  bool _isScanning = false;
  String? _errorMessage;

  Future<void> _scan() async {
    setState(() {
      _isScanning = true;
      _errorMessage = null;
    });

    try {
      final devices = await _discoveryService.scan();
      setState(() => _devices = devices);
    } catch (e) {
      setState(() => _errorMessage = 'Scan failed: $e');
    } finally {
      setState(() => _isScanning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Companion Link — Discovery Test')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ElevatedButton(
              onPressed: _isScanning ? null : _scan,
              child: Text(_isScanning ? 'Scanning...' : 'Scan for PC'),
            ),
            const SizedBox(height: 16),
            if (_errorMessage != null)
              Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
            Expanded(
              child: _devices.isEmpty
                  ? const Center(child: Text('No devices found yet'))
                  : ListView.builder(
                      itemCount: _devices.length,
                      itemBuilder: (context, index) {
                        final device = _devices[index];
                        return Card(
                          child: ListTile(
                            title: Text(device.deviceName),
                            subtitle: Text(
                              '${device.host}:${device.port}\n'
                              'ID: ${device.deviceId}',
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}