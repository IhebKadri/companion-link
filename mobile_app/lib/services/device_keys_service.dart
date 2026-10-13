import 'dart:convert';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class DeviceKeysService {
  static const _privateKeyStorageKey = 'companion_link_identity_private_key';

  final _storage = const FlutterSecureStorage();
  final _algorithm = X25519();

  Future<SimpleKeyPair> getOrCreateIdentityKeyPair() async {
    final stored = await _storage.read(key: _privateKeyStorageKey);
    if (stored != null) {
      final bytes = base64Decode(stored);
      return _algorithm.newKeyPairFromSeed(bytes);
    }

    final keyPair = await _algorithm.newKeyPair();
    final seed = await keyPair.extractPrivateKeyBytes();
    await _storage.write(
      key: _privateKeyStorageKey,
      value: base64Encode(seed),
    );
    return keyPair;
  }

  Future<Uint8List> getPublicKeyBytes(SimpleKeyPair keyPair) async {
    final publicKey = await keyPair.extractPublicKey();
    return Uint8List.fromList(publicKey.bytes);
  }
}