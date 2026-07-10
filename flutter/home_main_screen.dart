// lib/screens/home_main_screen.dart — v3 (기존 파일 교체)
// 변경: ① 종합 적합도가 최상단 큰 카드로 ② 기상 요인 카드마다 '그 요인의' 적합도 표시
//       ③ 아이콘 크기 10% 확대 ④ 피드백은 로딩 30초 후 하단 팝업, 평가하면 사라짐
//       ⑤ 추천 장소는 현재 활동 것만 (백엔드 activity 파라미터)
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'home_map_screen.dart';
import 'package:jejunowhere/globals.dart';
import 'package:jejunowhere/widget/tx.dart';
import 'package:jejunowhere/api_service.dart';

class HomeMainScreen extends StatefulWidget {
  final List<String> selectedActivities;

  const HomeMainScreen({super.key, required this.selectedActivities});

  @override
  State<HomeMainScreen> createState() => _HomeMainScreenState();
}

class _HomeMainScreenState extends State<HomeMainScreen> {
  int _currentIndex = 0;
  bool _isLoading = true;
  String _chip = '전체';

  double _lat = 33.4996, _lon = 126.5312; // GPS 실패 시 기본값(제주시내)
  bool _gpsResolved = false;

  Map<String, String> _aiData = {'title': '', 'desc': ''};
  Map<String, dynamic>? _current; // activities[현재활동] 원본 (score/phrase/factors/timeline)
  List<Map<String, dynamic>> _factors = [];
  List<Map<String, dynamic>> _places = [];
  String _regionLabel = '';

  // 피드백 팝업 (로딩 30초 뒤 표시, 활동별 1회)
  bool _showFeedback = false;
  final Set<String> _rated = {};
  Timer? _fbTimer;

  final Map<String, String> _activityIcons = {
    '러닝': 'running.png', '강아지산책': 'walk.png', '등산': 'climbing.png',
    '드론': 'drone.png', '쇼핑': 'shopping.png', '서핑': 'surfing.png',
    '골프': 'golf.png', '캠핑': 'camping.png',
  };

  String get _activity => widget.selectedActivities[_currentIndex];

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _fbTimer?.cancel();
    super.dispose();
  }

  Future<void> _init() async {
    await _resolveGps();
    await _loadApiData();
  }

  Future<void> _resolveGps() async {
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.always ||
          perm == LocationPermission.whileInUse) {
        final pos = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.high);
        _lat = pos.latitude;
        _lon = pos.longitude;
      }
    } catch (_) {}
    _gpsResolved = true;
  }

  void _onActivityChanged(int index) {
    setState(() {
      _currentIndex = index;
      _showFeedback = false;
    });
    _loadApiData();
  }

  void _scheduleFeedback() {
    _fbTimer?.cancel();
    if (_rated.contains(_activity)) return; // 이미 평가한 활동은 다시 안 물음
    _fbTimer = Timer(const Duration(seconds: 30), () {
      if (mounted && !_rated.contains(_activity)) {
        setState(() => _showFeedback = true);
      }
    });
  }

  Future<void> _loadApiData() async {
    setState(() => _isLoading = true);
    final act = _activity;

    try {
      final ai = await ApiService.getAiText(act, lat: _lat, lon: _lon);
      final sc = await ApiService.getScores(_lat, _lon);
      final pl = await ApiService.getRecommendations(_lat, _lon, activity: act);

      if (ai != null) {
        _aiData = {'title': ai['title'] ?? '', 'desc': ai['desc'] ?? '',
                   'outfit': ai['outfit'] ?? ''};
      }
      _places = pl;

      if (sc != null) {
        final w = (sc['weather'] ?? {}) as Map<String, dynamic>;
        _current = (sc['activities'] ?? {})[act];
        final factors =
            (_current?['factors'] ?? {}) as Map<String, dynamic>;
        final hourly = (sc['hourly'] as List?) ?? [];
        _regionLabel =
            '${sc['location']?['region'] ?? ''}, ${sc['location']?['city'] ?? ''}';

        String hLabel(int i) => i < hourly.length
            ? L('${hourly[i]['hour']}시', '${hourly[i]['hour']}:00',
                '${hourly[i]['hour']}时')
            : '-';
        String hv(int i, String k, String sfx) =>
            i < hourly.length && hourly[i][k] != null
                ? '${hourly[i][k]}$sfx'
                : '-';
        final times = [hLabel(0), hLabel(1), hLabel(2)];
        // 요인별 적합도 (백엔드 factors: feel/wsd/wsd_alt/pop3/pm25/uv/reh...)
        String fs(List<String> keys) {
          for (final k in keys) {
            if (factors[k] != null) return '${factors[k]}';
          }
          return '-';
        }

        _factors = [
          _factor('기온', 'temperature.png',
              L('현재 기온 ${w['tmp'] ?? '-'}°C, 체감 ${w['feel'] ?? '-'}°C입니다.',
                  'Now ${w['tmp'] ?? '-'}°C, feels like ${w['feel'] ?? '-'}°C.',
                  '当前气温${w['tmp'] ?? '-'}°C，体感${w['feel'] ?? '-'}°C。'),
              [hv(0, 'tmp', '°'), hv(1, 'tmp', '°'), hv(2, 'tmp', '°')],
              fs(['feel']), Colors.orange, times),
          _factor('바람', 'wind.png',
              L('현재 풍속은 ${w['wsd'] ?? '-'}m/s입니다.',
                  'Wind speed ${w['wsd'] ?? '-'}m/s.',
                  '当前风速${w['wsd'] ?? '-'}m/s。'),
              [hv(0, 'wsd', ''), hv(1, 'wsd', ''), hv(2, 'wsd', '')],
              fs(['wsd', 'wsd_alt']), Colors.green, times),
          _factor('강수확률', 'weather.png',
              L('3시간 내 최대 강수확률은 ${w['pop3'] ?? '-'}%입니다.',
                  'Max rain chance in 3h: ${w['pop3'] ?? '-'}%.',
                  '3小时内最大降水概率${w['pop3'] ?? '-'}%。'),
              [hv(0, 'pop', '%'), hv(1, 'pop', '%'), hv(2, 'pop', '%')],
              fs(['pop3']), Colors.blue, times),
          _factor('미세먼지', 'dust.png',
              L('초미세먼지 ${w['pm25'] ?? '-'}㎍/㎥, 자외선 ${w['uv'] ?? '-'} 수준입니다.',
                  'PM2.5 ${w['pm25'] ?? '-'}㎍/㎥, UV index ${w['uv'] ?? '-'}.',
                  'PM2.5为${w['pm25'] ?? '-'}㎍/㎥，紫外线${w['uv'] ?? '-'}。'),
              ['${w['pm25'] ?? '-'}', '${w['pm10'] ?? '-'}', '${w['uv'] ?? '-'}'],
              fs(['pm25', 'pm10']), Colors.green,
              [tr('미세먼지'), 'PM10', tr('자외선')]),
        ];
      }
    } catch (e) {
      debugPrint('Main Screen API Error: $e');
    }

    if (!mounted) return;
    setState(() => _isLoading = false);
    _scheduleFeedback(); // 화면 로딩 후 30초 뒤 피드백 팝업
  }

  Map<String, dynamic> _factor(String title, String icon, String desc,
          List<String> values, String score, Color c, List<String> times) =>
      {'title': title, 'icon': icon, 'desc': desc, 'values': values,
       'score': score, 'valColor': c, 'times': times};

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F6FF),
      body: SafeArea(
        child: Stack(
          children: [
            _isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const CircularProgressIndicator(
                            color: Colors.blueAccent),
                        const SizedBox(height: 12),
                        if (!_gpsResolved) TX('위치 확인 중...'),
                      ],
                    ),
                  )
                : Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20.0, vertical: 12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment:
                                  MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 12, vertical: 8),
                                  decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius:
                                          BorderRadius.circular(20)),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.location_on,
                                          color: Colors.blueAccent,
                                          size: 18),
                                      const SizedBox(width: 4),
                                      Text(_regionLabel,
                                          style: const TextStyle(
                                              fontSize: 13,
                                              fontWeight: FontWeight.bold)),
                                    ],
                                  ),
                                ),
                                Row(
                                  children: [
                                    ValueListenableBuilder<String>(
                                      valueListenable: appLang,
                                      builder: (context, lang, _) =>
                                          GestureDetector(
                                        onTap: () {
                                          cycleLang();
                                          _loadApiData();
                                        },
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 10, vertical: 6),
                                          decoration: BoxDecoration(
                                            color: Colors.white,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                          ),
                                          child: Text(langLabel,
                                              style: const TextStyle(
                                                  fontSize: 12,
                                                  fontWeight:
                                                      FontWeight.bold)),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    GestureDetector(
                                      onTap: () {
                                        Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                            builder: (context) =>
                                                HomeMapScreen(
                                              selectedActivities:
                                                  widget.selectedActivities,
                                              initialIndex: _currentIndex,
                                            ),
                                          ),
                                        );
                                      },
                                      child: const Icon(Icons.map_outlined,
                                          size: 29, color: Colors.black87),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 20),

                            Text(_aiData['desc'] ?? '',
                                style: const TextStyle(
                                    fontSize: 17,
                                    fontWeight: FontWeight.bold,
                                    height: 1.4,
                                    color: Colors.black87)),
                            const SizedBox(height: 16),

                            Row(
                              children: [
                                _buildChip('전체'),
                                const SizedBox(width: 8),
                                _buildChip('기상기후'),
                                const SizedBox(width: 8),
                                _buildChip('코스'),
                                const Spacer(),
                                TX('Ai 추천순',
                                    style: const TextStyle(
                                        fontSize: 12, color: Colors.grey)),
                                const Icon(Icons.filter_alt_outlined,
                                    size: 16, color: Colors.grey),
                              ],
                            ),
                          ],
                        ),
                      ),

                      Expanded(child: _buildBody()),

                      Container(
                        height: 100,
                        width: double.infinity,
                        decoration: const BoxDecoration(
                          color: Color(0xFF90C2FF),
                          borderRadius: BorderRadius.only(
                              topLeft: Radius.circular(30),
                              topRight: Radius.circular(30)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: List.generate(
                              widget.selectedActivities.length, (index) {
                            final actName =
                                widget.selectedActivities[index];
                            final isSelected = _currentIndex == index;
                            return GestureDetector(
                              onTap: () => _onActivityChanged(index),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 16.0),
                                child: AnimatedOpacity(
                                  duration:
                                      const Duration(milliseconds: 200),
                                  opacity: isSelected ? 1.0 : 0.4,
                                  child: Image.asset(
                                    'assets/icons/${_activityIcons[actName] ?? 'running.png'}',
                                    // 아이콘 10% 확대 (50→55, 40→44)
                                    width: isSelected ? 55 : 44,
                                    height: isSelected ? 55 : 44,
                                  ),
                                ),
                              ),
                            );
                          }),
                        ),
                      ),
                    ],
                  ),

            // ④ 피드백 팝업 — 30초 뒤 하단에서 등장, 1회 평가 후 사라짐
            AnimatedPositioned(
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeOut,
              left: 20,
              right: 20,
              bottom: _showFeedback ? 116 : -120,
              child: _feedbackPopup(),
            ),
          ],
        ),
      ),
    );
  }

  // 종합 적합도 히어로 카드 — 연한 하늘색, 3:4 비율
  // [왼쪽 절반: 활동 아이콘] [가운데: 추천 의상] [오른쪽: 적합도]
  Widget _overallCard() {
    final score = _current?['score']?.toString() ?? '-';
    final phrase = _current?['phrase']?.toString() ?? '';
    final veto = _current?['veto'];
    final color = veto != null
        ? Colors.red
        : (int.tryParse(score) ?? 0) >= 70
            ? Colors.green
            : (int.tryParse(score) ?? 0) >= 40
                ? Colors.orange
                : Colors.red;
    final outfits = (_aiData['outfit'] ?? '')
        .split(' · ')
        .where((s) => s.trim().isNotEmpty)
        .toList();

    return AspectRatio(
      aspectRatio: 4 / 3, // 가로 4 : 세로 3
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFFE3F0FF), // 살짝 연한 하늘색
          borderRadius: BorderRadius.circular(28),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // 왼쪽 절반: 활동 아이콘 크게
            Expanded(
              flex: 5,
              child: Center(
                child: Image.asset(
                  'assets/icons/${_activityIcons[_activity] ?? 'running.png'}',
                  fit: BoxFit.contain,
                ),
              ),
            ),
            const SizedBox(width: 12),
            // 가운데: 추천 의상
            Expanded(
              flex: 3,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TX('추천 의상',
                      style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.blueGrey)),
                  const SizedBox(height: 8),
                  ...outfits.take(5).map((o) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(o,
                              style: const TextStyle(fontSize: 11),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis),
                        ),
                      )),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // 오른쪽: 적합도
            Expanded(
              flex: 3,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  TX(_activity,
                      style: const TextStyle(
                          fontSize: 14, fontWeight: FontWeight.bold)),
                  TX('적합도',
                      style: const TextStyle(
                          fontSize: 12, color: Colors.blueGrey)),
                  const SizedBox(height: 6),
                  Text(score,
                      style: TextStyle(
                          fontSize: 52,
                          fontWeight: FontWeight.bold,
                          color: color)),
                  const SizedBox(height: 6),
                  Text(phrase,
                      textAlign: TextAlign.right,
                      style: const TextStyle(
                          fontSize: 11, color: Colors.blueGrey),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _feedbackPopup() {
    return Material(
      elevation: 8,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(20)),
        child: Row(
          children: [
            Expanded(
              child: TX('이 추천이 어땠나요?',
                  style: const TextStyle(
                      fontSize: 13, fontWeight: FontWeight.bold)),
            ),
            _feedbackButton(true),
            const SizedBox(width: 6),
            _feedbackButton(false),
          ],
        ),
      ),
    );
  }

  Widget _feedbackButton(bool good) {
    return GestureDetector(
      onTap: () async {
        final act = _activity;
        setState(() {
          _rated.add(act);       // 한 번 수집하면 다시 안 뜸 (신뢰성)
          _showFeedback = false;
        });
        final res =
            await ApiService.sendFeedback(act, good, lat: _lat, lon: _lon);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 2),
            content: Text(res != null
                ? tr('평가가 저장되었습니다. 감사합니다!')
                : tr('전송에 실패했어요. 잠시 후 다시 시도해주세요.')),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: good ? const Color(0xFFEAF3FF) : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Text(good ? '👍' : '👎', style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 4),
            TX(good ? '좋았어요' : '별로예요',
                style: const TextStyle(fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    final children = <Widget>[
      // 종합 적합도 카드 — 추천 문구 바로 아래, 3:4 히어로 카드
      _overallCard(),
      const SizedBox(height: 20),
    ];
    if (_chip != '코스') {
      children.addAll(_factors.map(_factorCard));
    }
    if (_chip != '기상기후') {
      if (_chip == '전체' && _places.isNotEmpty) {
        children.add(Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: TX('추천 장소',
              style:
                  const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        ));
      }
      children.addAll(_places.map(_placeCard));
    }
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
      children: children,
    );
  }

  Widget _factorCard(Map<String, dynamic> f) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20)),
            child: Text(f['desc'],
                style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.black87)),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24)),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  children: [
                    Image.asset('assets/icons/${f['icon']}',
                        width: 46, height: 46), // 기상 아이콘 확대
                    const SizedBox(height: 4),
                    TX(f['title'],
                        style: const TextStyle(
                            fontSize: 11, color: Colors.grey)),
                  ],
                ),
                _timeCol(f['times'][0], f['values'][0], f['valColor']),
                _timeCol(f['times'][1], f['values'][1], f['valColor']),
                _timeCol(f['times'][2], f['values'][2], f['valColor']),
                Column(
                  children: [
                    TX('적합도',
                        style: const TextStyle(
                            fontSize: 12, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    // ② 이 기상 요인의 개별 적합도 (활동 종합점수 아님)
                    Text(f['score'],
                        style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Colors.green)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _placeCard(Map<String, dynamic> p) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: p['image'] != null
                ? Image.network(p['image'], width: 88, height: 88,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _imgFallback())
                : _imgFallback(),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${p['name']} (${p['distance']}km)',
                    style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.bold),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                Text('${p['address'] ?? ''}',
                    style:
                        const TextStyle(fontSize: 11, color: Colors.grey),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 6),
                Row(
                  children: [
                    TX('${p['activity']}',
                        style: const TextStyle(
                            fontSize: 11,
                            color: Colors.blueAccent,
                            fontWeight: FontWeight.bold)),
                    const Spacer(),
                    TX('적합도',
                        style: const TextStyle(
                            fontSize: 11, fontWeight: FontWeight.bold)),
                    const SizedBox(width: 6),
                    Text('${p['score']}',
                        style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.green)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _imgFallback() => Container(
      width: 88,
      height: 88,
      color: Colors.blue.shade50,
      child: const Icon(Icons.photo, color: Colors.blueAccent));

  Widget _buildChip(String label) {
    final isSelected = _chip == label;
    return GestureDetector(
      onTap: () => setState(() => _chip = label),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : Colors.transparent,
          border: Border.all(
              color:
                  isSelected ? Colors.blueAccent : Colors.grey.shade300),
          borderRadius: BorderRadius.circular(20),
        ),
        child: TX(label,
            style: TextStyle(
                fontSize: 12,
                color: isSelected ? Colors.blueAccent : Colors.grey,
                fontWeight:
                    isSelected ? FontWeight.bold : FontWeight.normal)),
      ),
    );
  }

  Widget _timeCol(String time, String value, Color valColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4.0),
      child: Column(
        children: [
          Text(time,
              style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87)),
          const SizedBox(height: 8),
          Text(value,
              style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: valColor)),
        ],
      ),
    );
  }
}
