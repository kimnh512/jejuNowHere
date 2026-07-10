// lib/widget/tx.dart — 3개 언어(ko/en/zh) 번역 위젯 (기존 파일 교체)
// Text(...) 자리에 TX(...)를 쓰면 appLang에 따라 자동 번역됩니다.
// 정적 UI 라벨은 아래 사전으로, API에서 오는 동적 문장은 서버(/nlg?lang=..)가
// 이미 해당 언어로 생성하므로 사전에 없어도 됩니다 (원문 그대로 출력).
import 'package:flutter/material.dart';
import 'package:jejunowhere/globals.dart';

const Map<String, Map<String, String>> _dict = {
  // ── 공통 · 라이프스타일 화면 ──────────────────────────────
  '반갑습니다': {'en': 'Welcome', 'zh': '欢迎您'},
  '이름을 입력해주세요': {'en': 'Enter your name', 'zh': '请输入您的名字'},
  '시작하기': {'en': 'Start', 'zh': '开始'},
  '당신의 라이프스타일에 적합한 활동들을\n최소 1개에서 최대 5개까지 골라주세요.': {
    'en': 'Pick 1 to 5 activities\nthat fit your lifestyle.',
    'zh': '请选择1到5个适合您生活方式的活动。'
  },
  '(새로운 라이프스타일이 지속 업데이트 중입니다)': {
    'en': '(New lifestyles are continuously added)',
    'zh': '(新生活方式正在持续更新中)'
  },
  '선택완료': {'en': 'Done', 'zh': '选择完成'},
  '최대 5개까지만 선택할 수 있어요!': {
    'en': 'You can select up to 5!',
    'zh': '最多只能选择5个！'
  },

  // ── 활동명 ───────────────────────────────────────────────
  '러닝': {'en': 'Running', 'zh': '跑步'},
  '강아지산책': {'en': 'Dog walk', 'zh': '遛狗'},
  '등산': {'en': 'Hiking', 'zh': '登山'},
  '드론': {'en': 'Drone', 'zh': '无人机'},
  '쇼핑': {'en': 'Shopping', 'zh': '购物'},
  '서핑': {'en': 'Surfing', 'zh': '冲浪'},
  '골프': {'en': 'Golf', 'zh': '高尔夫'},
  '캠핑': {'en': 'Camping', 'zh': '露营'},

  // ── 메인 화면 ────────────────────────────────────────────
  '전체': {'en': 'All', 'zh': '全部'},
  '기상기후': {'en': 'Weather', 'zh': '气象气候'},
  '코스': {'en': 'Places', 'zh': '路线'},
  'Ai 추천순': {'en': 'AI ranked', 'zh': 'AI 推荐顺序'},
  '적합도': {'en': 'Score', 'zh': '适合度'},
  '기온': {'en': 'Temp', 'zh': '气温'},
  '바람': {'en': 'Wind', 'zh': '风'},
  '미세먼지': {'en': 'Air', 'zh': '微尘'},
  '강수확률': {'en': 'Rain %', 'zh': '降水概率'},
  '자외선': {'en': 'UV', 'zh': '紫外线'},
  '위치 확인 중...': {'en': 'Locating...', 'zh': '定位中...'},
  '추천 장소': {'en': 'Recommended places', 'zh': '推荐地点'},

  // ── 피드백 ───────────────────────────────────────────────
  '이 추천이 어땠나요?': {'en': 'How was this recommendation?', 'zh': '这个推荐怎么样？'},
  '좋았어요': {'en': 'Good', 'zh': '很好'},
  '별로예요': {'en': 'Not good', 'zh': '不太好'},
  '평가가 저장되었습니다. 감사합니다!': {
    'en': 'Feedback saved. Thank you!',
    'zh': '评价已保存，谢谢！'
  },
  '전송에 실패했어요. 잠시 후 다시 시도해주세요.': {
    'en': 'Failed to send. Please try again.',
    'zh': '发送失败，请稍后再试。'
  },

  // ── 지도 화면 ────────────────────────────────────────────
  '내 주변 추천 지역': {'en': 'Recommended nearby', 'zh': '我附近的推荐区域'},
  '추천 점수': {'en': 'Score', 'zh': '推荐分数'},
  '추천 장소가 없습니다. 잠시 후 다시 시도해주세요.': {
    'en': 'No places found. Please try again shortly.',
    'zh': '暂无推荐地点，请稍后再试。'
  },
};

/// 사전 조회 (없으면 원문 반환 — API가 언어별로 생성한 문장은 그대로 통과)
String tr(String text) {
  if (appLang.value == 'ko') return text;
  return _dict[text]?[appLang.value] ?? text;
}

class TX extends StatelessWidget {
  final String text;
  final TextStyle? style;
  final int? maxLines;
  final TextOverflow? overflow;
  final TextAlign? textAlign;

  const TX(
    this.text, {
    super.key,
    this.style,
    this.maxLines,
    this.overflow,
    this.textAlign,
  });

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: appLang,
      builder: (context, lang, child) {
        return Text(tr(text),
            style: style,
            maxLines: maxLines,
            overflow: overflow,
            textAlign: textAlign);
      },
    );
  }
}
