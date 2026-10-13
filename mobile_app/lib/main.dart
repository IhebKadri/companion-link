import 'package:flutter/material.dart';

import 'screens/pairing_screen.dart';

void main() {
  runApp(const CompanionLinkApp());
}

class CompanionLinkApp extends StatelessWidget {
  const CompanionLinkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Companion Link',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: const PairingScreen(),
    );
  }
}