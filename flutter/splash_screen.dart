// lib/screens/splash_screen.dart — v2 (기존 파일 교체)
// 변경: 서버 미리 깨우기 + 이름 미입력 시 NameScreen으로 이동
import 'package:flutter/material.dart';
import 'dart:async';
import 'package:jejunowhere/globals.dart';
import 'package:jejunowhere/api_service.dart';
import 'package:jejunowhere/screens/lifestyle_screen.dart';
import 'package:jejunowhere/screens/name_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    ApiService.warmUp(); // 스플래시 2.5초 동안 Render 서버를 미리 깨움

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _fadeAnimation =
        Tween<double>(begin: 0.0, end: 1.0).animate(_animationController);
    _animationController.forward();

    Timer(const Duration(milliseconds: 2500), () {
      // 이름을 아직 안 받았으면 이름 입력 화면부터
      final next = userName.value.isEmpty
          ? const NameScreen()
          : const LifestyleScreen();
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => next,
          transitionsBuilder:
              (context, animation, secondaryAnimation, child) {
            return FadeTransition(opacity: animation, child: child);
          },
          transitionDuration: const Duration(milliseconds: 800),
        ),
      );
    });
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 기존 스플래시 UI 그대로 유지 — 로고/배경은 원래 파일의 build 내용을 쓰세요.
    return Scaffold(
      backgroundColor: const Color(0xFF90C2FF),
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: const Text(
            'JEJU NOWHERE',
            style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: Colors.white,
                letterSpacing: 2),
          ),
        ),
      ),
    );
  }
}
