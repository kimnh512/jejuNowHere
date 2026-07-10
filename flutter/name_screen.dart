// lib/screens/name_screen.dart — 새 파일: 이름 입력 후 시작
import 'package:flutter/material.dart';
import 'package:jejunowhere/globals.dart';
import 'package:jejunowhere/widget/tx.dart';
import 'lifestyle_screen.dart';

class NameScreen extends StatefulWidget {
  const NameScreen({super.key});

  @override
  State<NameScreen> createState() => _NameScreenState();
}

class _NameScreenState extends State<NameScreen> {
  final _controller = TextEditingController();

  void _start() {
    final name = _controller.text.trim();
    if (name.isEmpty) return;
    userName.value = name;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LifestyleScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F6FF),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 언어 버튼 (첫 화면부터 언어 선택 가능)
              Align(
                alignment: Alignment.topRight,
                child: ValueListenableBuilder<String>(
                  valueListenable: appLang,
                  builder: (context, lang, _) => GestureDetector(
                    onTap: cycleLang,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.blueAccent,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(langLabel,
                          style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold)),
                    ),
                  ),
                ),
              ),
              const Spacer(),
              TX('반갑습니다',
                  style: const TextStyle(
                      fontSize: 26, fontWeight: FontWeight.bold)),
              const SizedBox(height: 24),
              TextField(
                controller: _controller,
                onSubmitted: (_) => _start(),
                decoration: InputDecoration(
                  hintText: tr('이름을 입력해주세요'),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                height: 54,
                child: ElevatedButton(
                  onPressed: _start,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF90C2FF),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    elevation: 0,
                  ),
                  child: TX('시작하기',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.bold)),
                ),
              ),
              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }
}
