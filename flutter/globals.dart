// lib/globals.dart — 앱 전역 상태 (기존 파일 교체)
// 변경: isChineseMode(한/중 2단) → appLang(ko/en/zh 3단) + 사용자 이름
import 'package:flutter/material.dart';

/// 현재 언어: 'ko' | 'en' | 'zh'
final ValueNotifier<String> appLang = ValueNotifier('ko');

/// 사용자 이름 (앱 시작 시 입력)
final ValueNotifier<String> userName = ValueNotifier('');

/// 언어 순환: KR → EN → CN → KR  (언어 버튼에서 호출)
void cycleLang() {
  const order = ['ko', 'en', 'zh'];
  final i = order.indexOf(appLang.value);
  appLang.value = order[(i + 1) % order.length];
}

/// 언어 버튼에 표시할 라벨
String get langLabel =>
    {'ko': '🇰🇷 KR', 'en': '🇺🇸 EN', 'zh': '🇨🇳 CN'}[appLang.value]!;

/// 동적 문장(숫자가 들어가는 문구)용 즉석 3개 언어 선택 헬퍼.
/// 예: L('기온 $t도', 'Temp $t°C', '气温 $t度')
String L(String ko, String en, String zh) {
  switch (appLang.value) {
    case 'en':
      return en;
    case 'zh':
      return zh;
    default:
      return ko;
  }
}
