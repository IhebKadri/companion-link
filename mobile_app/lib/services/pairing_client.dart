import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

import 'device_keys_service.dart';

class PairingResult {
  PairingResult({required this.pcPublicKeyBytes, required this.sharedKey});

  final Uint8List pcPublicKeyBytes;
  final SecretKey sharedKey;
}

class PairingException implements Exception {
  PairingException(this.message);
  final String message;

  @override
  String toString() => 'PairingException: $message';
}

class PairingClient {
  static const int pairingPort = 51821;
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration responseTimeout = Duration(seconds: 10);

  final _algorithm = X25519();
  final _deviceKeysService = DeviceKeysService();

  Future<PairingResult> pair({
    required String pcHost,
    required String code,
    required String deviceName,
  }) async {
    final keyPair = await _deviceKeysService.getOrCreateIdentityKeyPair();
    final publicKeyBytes = await _deviceKeysService.getPublicKeyBytes(keyPair);

    Socket socket;
    try {
      socket = await Socket.connect(pcHost, pairingPort, timeout: connectTimeout);
    } on SocketException catch (e) {
      throw PairingException('Could not connect to PC: ${e.message}');
    }

    try {
      final request = jsonEncode({
        'type': 'pair_request',
        'code': code,
        'public_key': _bytesToHex(publicKeyBytes),
        'device_name': deviceName,
      });
      socket.write('$request\n');
      await socket.flush();

      final responseLine = await socket
          .cast<List<int>>()
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .first
          .timeout(responseTimeout);

      final response = jsonDecode(responseLine) as Map<String, dynamic>;

      if (response['status'] != 'ok') {
        throw PairingException(response['message'] as String? ?? 'Pairing failed');
      }

      final pcPublicKeyHex = response['public_key'] as String;
      final pcPublicKeyBytes = _hexToBytes(pcPublicKeyHex);

      final pcPublicKey = SimplePublicKey(pcPublicKeyBytes, type: KeyPairType.x25519);
      final sharedSecret = await _algorithm.sharedSecretKey(
        keyPair: keyPair,
        remotePublicKey: pcPublicKey,
      );

      final hkdf = Hkdf(hmac: Hmac.sha256(), outputLength: 32);
      final derivedKey = await hkdf.deriveKey(
        secretKey: sharedSecret,
        info: utf8.encode('companion-link-pairing-v1'),
      );

      return PairingResult(pcPublicKeyBytes: pcPublicKeyBytes, sharedKey: derivedKey);
    } on FormatException {
      throw PairingException('Received malformed response from PC');
    } finally {
      await socket.close();
    }
  }

  String _bytesToHex(Uint8List bytes) =>
      bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

  Uint8List _hexToBytes(String hex) {
    final result = Uint8List(hex.length ~/ 2);
    for (var i = 0; i < hex.length; i += 2) {
      result[i ~/ 2] = int.parse(hex.substring(i, i + 2), radix: 16);
    }
    return result;
  }
}