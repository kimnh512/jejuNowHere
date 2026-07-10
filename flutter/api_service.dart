// lib/api_service.dart — 제주나우히어 백엔드 연동 (D:\jejunowhere\lib\ 에 넣기)
//
// 화면 계약에 맞춘 어댑터:
//   ApiService.getAiText(activity)            → {'title','desc'}   (/nlg, 中/韓 자동)
//   ApiService.getScores(lat, lon)            → temp_desc 등 + 원본 전체 (/scores)
//   ApiService.getRecommendations(lat, lon)   → name/address/lat/lng/distance (/recommend)
//   ApiService.sendFeedback(activity, good)   → 좋았어요/별로 (POST /feedback)
//   ApiService.warmUp()                       → 스플래시에서 서버 깨우기
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:jejunowhere/globals.dart'; // appLang (ko/en/zh)

class ApiService {
  static const String base = 'https://jejunowhere.onrender.com';
  static String get _lang => appLang.value; // 'ko' | 'en' | 'zh'

  // ── 공통 GET: 60초 타임아웃(Render 첫 요청은 잠 깨는 시간),
  //    제주 밖 좌표(422)면 제주시내로 자동 폴백 (에뮬레이터 대응)
  static Future<Map<String, dynamic>?> _get(
      String path, Map<String, String> q) async {
    try {
      var res = await http
          .get(Uri.parse('$base$path').replace(queryParameters: q))
          .timeout(const Duration(seconds: 60));
      if (res.statusCode == 422 && q.containsKey('lat')) {
        final q2 = Map<String, String>.from(q)
          ..remove('lat')
          ..remove('lon')
          ..['region'] = '제주시내';
        res = await http
            .get(Uri.parse('$base$path').replace(queryParameters: q2))
            .timeout(const Duration(seconds: 60));
      }
      if (res.statusCode != 200) return null;
      // 한글 깨짐 방지: 반드시 bodyBytes를 utf8로 디코딩
      return jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      return null; // 화면의 fallback 데이터가 대신 사용됨
    }
  }

  /// 스플래시에서 호출 — Render 무료 서버를 미리 깨워 첫 화면 지연 제거
  static void warmUp() {
    http.get(Uri.parse('$base/health')).catchError((_) => http.Response('', 0));
  }

  /// GPT 문구 (/nlg): title=장소 소개, desc=추천 문장.
  /// 중국어 모드면 자동으로 lang=zh. 캠핑 등 미지원 활동은 null → 화면 fallback.
  static Future<Map<String, String>?> getAiText(String activity,
      {double lat = 33.4996, double lon = 126.5312, String? place}) async {
    final d = await _get('/nlg', {
      'activity': activity,
      'lat': '$lat',
      'lon': '$lon',
      'lang': _lang,
      if (place != null) 'place': place,
    });
    if (d == null) return null;
    return {
      'title': (d['place_intro'] ?? '').toString(),
      'desc': (d['recommendation_message'] ?? '').toString(),
      // 추천 의상 리스트 → '볼캡 · 반팔 티셔츠 · ...' 형태
      'outfit': ((d['outfit'] as List?) ?? []).join(' · '),
    };
  }

  /// 점수+날씨 (/scores): 기존 계약 키(temp_desc 등) + 원본 전체를 함께 반환.
  /// 원본 키: location, weather, activities(점수·문구·타임라인), hourly, best_regions
  static Future<Map<String, dynamic>?> getScores(double lat, double lon) async {
    final d = await _get('/scores', {'lat': '$lat', 'lon': '$lon'});
    if (d == null) return null;
    final w = (d['weather'] ?? {}) as Map<String, dynamic>;
    d['temp_desc'] = '현재 기온 ${w['tmp'] ?? '-'}°C, 체감 ${w['feel'] ?? '-'}°C입니다.';
    d['wind_desc'] = '현재 풍속은 ${w['wsd'] ?? '-'}m/s입니다.';
    d['dust_desc'] = '초미세먼지 ${w['pm25'] ?? '-'}㎍/㎥ 수준입니다.';
    return d;
  }

  /// 장소 추천 (/recommend): 지도 화면 계약(lng, distance)으로 키 변환.
  /// activity 지정 시 그 활동에 적합한 장소만 (골프→골프장, 러닝→공원).
  static Future<List<Map<String, dynamic>>> getRecommendations(
      double lat, double lon, {String? activity}) async {
    final d = await _get('/recommend', {
      'lat': '$lat', 'lon': '$lon',
      if (activity != null) 'activity': activity,
    });
    final places = (d?['places'] as List?) ?? [];
    return places
        .map<Map<String, dynamic>>((p) => {
              'name': p['name'],
              'address': p['address'],
              'lat': p['lat'],
              'lng': p['lon'], // 백엔드는 lon, 지도 화면은 lng
              'distance': p['dist_km'],
              'activity': p['activity'],
              'score': p['score'],
              'category': p['category'],
              'url': p['url'],
            })
        .toList();
  }

  /// 평가 전송 (POST /feedback) — ML 학습 데이터. 활동별 30건부터 자동 재학습.
  /// 성공 시 {total_for_activity, needed_for_ml, retrained} 반환, 실패 시 null.
  static Future<Map<String, dynamic>?> sendFeedback(String activity, bool good,
      {double lat = 33.4996, double lon = 126.5312}) async {
    try {
      final res = await http.post(
        Uri.parse('$base/feedback'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
            {'activity': activity, 'good': good, 'lat': lat, 'lon': lon}),
      );
      if (res.statusCode != 200) return null;
      return jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }
}
