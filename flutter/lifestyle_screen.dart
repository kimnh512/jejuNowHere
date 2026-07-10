// lib/screens/lifestyle_screen.dart — 이름 인사 + 3개 언어 버튼 (기존 파일 교체)
import 'package:flutter/material.dart';
import 'home_main_screen.dart';
import 'package:jejunowhere/globals.dart';
import 'package:jejunowhere/widget/tx.dart';

class LifestyleScreen extends StatefulWidget {
  const LifestyleScreen({super.key});

  @override
  State<LifestyleScreen> createState() => _LifestyleScreenState();
}

class _LifestyleScreenState extends State<LifestyleScreen> {
  final List<Map<String, String>> activities = [
    {'name': '러닝', 'icon': 'running.png'},
    {'name': '강아지산책', 'icon': 'walk.png'},
    {'name': '등산', 'icon': 'climbing.png'},
    {'name': '드론', 'icon': 'drone.png'},
    {'name': '쇼핑', 'icon': 'shopping.png'},
    {'name': '서핑', 'icon': 'surfing.png'},
    {'name': '골프', 'icon': 'golf.png'},
    {'name': '캠핑', 'icon': 'camping.png'},
  ];

  List<String> selectedActivities = [];

  void toggleSelection(String name) {
    setState(() {
      if (selectedActivities.contains(name)) {
        selectedActivities.remove(name);
      } else {
        if (selectedActivities.length < 5) {
          selectedActivities.add(name);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: TX('최대 5개까지만 선택할 수 있어요!'),
                duration: const Duration(seconds: 1)),
          );
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F6FF),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. 언어 버튼 (KR → EN → CN 순환)
            Padding(
              padding: const EdgeInsets.only(top: 16, right: 24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  ValueListenableBuilder<String>(
                    valueListenable: appLang,
                    builder: (context, lang, child) {
                      return GestureDetector(
                        onTap: cycleLang,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 8),
                          decoration: BoxDecoration(
                            color: lang == 'zh'
                                ? Colors.redAccent
                                : lang == 'en'
                                    ? Colors.indigo
                                    : Colors.blueAccent,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(langLabel,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold)),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),

            // 2. 타이틀 — 입력받은 이름으로 인사
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 10, 24, 20),
              child: ValueListenableBuilder<String>(
                valueListenable: appLang,
                builder: (context, lang, child) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        L('반갑습니다, ${userName.value}님!',
                            'Welcome, ${userName.value}!',
                            '欢迎您，${userName.value}！'),
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 8),
                      TX(
                        '당신의 라이프스타일에 적합한 활동들을\n최소 1개에서 최대 5개까지 골라주세요.',
                        style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            height: 1.4),
                      ),
                      const SizedBox(height: 12),
                      TX(
                        '(새로운 라이프스타일이 지속 업데이트 중입니다)',
                        style:
                            const TextStyle(fontSize: 13, color: Colors.grey),
                      ),
                    ],
                  );
                },
              ),
            ),

            // 3. 활동 그리드
            Expanded(
              child: GridView.builder(
                physics: const NeverScrollableScrollPhysics(),
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3,
                  childAspectRatio: 0.9,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 10,
                ),
                itemCount: activities.length,
                itemBuilder: (context, index) {
                  final activity = activities[index];
                  final isSelected =
                      selectedActivities.contains(activity['name']);
                  return GestureDetector(
                    onTap: () => toggleSelection(activity['name']!),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Image.asset(
                              'assets/icons/${activity['icon']}',
                              height: 45,
                              fit: BoxFit.contain),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? Colors.white
                                : Colors.transparent,
                            border: Border.all(
                                color: isSelected
                                    ? const Color(0xFF3A6FF8)
                                    : Colors.transparent,
                                width: 1.5),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: TX(
                            activity['name']!,
                            style: TextStyle(
                              color: isSelected
                                  ? const Color(0xFF3A6FF8)
                                  : Colors.grey.shade600,
                              fontWeight: isSelected
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),

            // 4. 완료 버튼
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  onPressed: selectedActivities.isEmpty
                      ? null
                      : () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => HomeMainScreen(
                                  selectedActivities: selectedActivities),
                            ),
                          );
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF90C2FF),
                    disabledBackgroundColor: Colors.grey.shade300,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    elevation: 0,
                  ),
                  child: TX(
                    '선택완료',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
