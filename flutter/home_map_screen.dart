// lib/screens/home_map_screen.dart — v2 (기존 파일 교체)
// 변경: 하드코딩 가짜 코스 제거, 카카오 이미지 카드, 실제 점수·태그(활동/카테고리)
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:jejunowhere/globals.dart';
import 'package:jejunowhere/widget/tx.dart';
import 'package:jejunowhere/api_service.dart';

class HomeMapScreen extends StatefulWidget {
  final List<String> selectedActivities;
  final int initialIndex;

  const HomeMapScreen({
    super.key,
    required this.selectedActivities,
    required this.initialIndex,
  });

  @override
  State<HomeMapScreen> createState() => _HomeMapScreenState();
}

class _HomeMapScreenState extends State<HomeMapScreen> {
  late int _currentIndex;
  int _selectedSpotIndex = 0;

  GoogleMapController? _mapController;

  LatLng _currentPosition = const LatLng(33.4996, 126.5312);
  bool _isLoadingLocation = true;
  bool _isLoadingRecommendations = true;

  final Map<String, String> _activityIcons = {
    '러닝': 'running.png', '강아지산책': 'walk.png', '등산': 'climbing.png',
    '드론': 'drone.png', '쇼핑': 'shopping.png', '서핑': 'surfing.png',
    '골프': 'golf.png', '캠핑': 'camping.png',
  };

  List<Map<String, dynamic>> _recommendedSpots = [];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
    _initScreen();
  }

  Future<void> _initScreen() async {
    await _getUserCurrentLocation();
    await _loadRecommendations();
  }

  Future<void> _getUserCurrentLocation() async {
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse) {
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      if (!mounted) return;
      setState(() {
        _currentPosition = LatLng(position.latitude, position.longitude);
        _isLoadingLocation = false;
      });

      _mapController?.animateCamera(CameraUpdate.newLatLng(_currentPosition));
    } else {
      if (!mounted) return;
      setState(() {
        _isLoadingLocation = false;
      });
    }
  }

  // 💡 추천 장소 로드 — API 실데이터만 사용 (하드코딩 제거)
  Future<void> _loadRecommendations() async {
    setState(() => _isLoadingRecommendations = true);

    List<Map<String, dynamic>> realSpots = [];
    try {
      // 현재 선택된 활동의 장소만 추천 (골프 탭 → 골프장만)
      final apiData = await ApiService.getRecommendations(
        _currentPosition.latitude,
        _currentPosition.longitude,
        activity: widget.selectedActivities[_currentIndex],
      );
      for (var item in apiData) {
        realSpots.add({
          'title': item['name'] ?? '',
          'desc': item['address'] ?? '',
          'latLng': LatLng(
            double.parse(item['lat'].toString()),
            double.parse(item['lng'].toString()),
          ),
          'distance': '${item['distance']}km',
          'tags': [item['activity'] ?? '', item['category'] ?? ''],
          'score': '${item['score'] ?? '-'}',
          'image': item['image'], // 카카오 이미지 검색 결과 (null 가능)
        });
      }
    } catch (e) {
      debugPrint('Map API Error: $e');
    }

    if (!mounted) return;
    setState(() {
      _recommendedSpots = realSpots;
      _selectedSpotIndex = 0;
      _isLoadingRecommendations = false;
    });

    if (realSpots.isNotEmpty) {
      _mapController
          ?.animateCamera(CameraUpdate.newLatLng(realSpots[0]['latLng']));
    }
  }

  void _onSpotChanged(int index) {
    setState(() => _selectedSpotIndex = index);
    _mapController?.animateCamera(
      CameraUpdate.newLatLng(_recommendedSpots[index]['latLng']),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoadingLocation
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF3A6FF8)))
          : Stack(
              children: [
                GoogleMap(
                  initialCameraPosition:
                      CameraPosition(target: _currentPosition, zoom: 12.5),
                  mapType: MapType.normal,
                  myLocationEnabled: true,
                  myLocationButtonEnabled: false,
                  zoomControlsEnabled: false,
                  onMapCreated: (controller) {
                    _mapController = controller;
                  },
                  markers: _recommendedSpots.asMap().entries.map((entry) {
                    int index = entry.key;
                    var spot = entry.value;
                    return Marker(
                      markerId: MarkerId('spot_$index'),
                      position: spot['latLng'],
                      infoWindow: InfoWindow(
                          title: spot['title'], snippet: spot['distance']),
                      icon: BitmapDescriptor.defaultMarkerWithHue(
                        _selectedSpotIndex == index
                            ? BitmapDescriptor.hueAzure
                            : BitmapDescriptor.hueRed,
                      ),
                      onTap: () => _onSpotChanged(index),
                    );
                  }).toSet(),
                ),

                // 상단 앱바
                SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20.0, vertical: 12.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            GestureDetector(
                              onTap: () => Navigator.pop(context),
                              child: Container(
                                padding: const EdgeInsets.all(8),
                                decoration: const BoxDecoration(
                                    color: Colors.white,
                                    shape: BoxShape.circle),
                                child: const Icon(Icons.arrow_back, size: 20),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 8),
                              decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(20),
                                  boxShadow: const [
                                    BoxShadow(
                                        color: Colors.black12, blurRadius: 4)
                                  ]),
                              child: TX('내 주변 추천 지역',
                                  style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.bold)),
                            ),
                          ],
                        ),
                        // 언어 버튼
                        ValueListenableBuilder<String>(
                          valueListenable: appLang,
                          builder: (context, lang, _) => GestureDetector(
                            onTap: () {
                              cycleLang();
                              setState(() {});
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(20)),
                              child: Text(langLabel,
                                  style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // 드래그 가능한 추천 리스트
                Positioned(
                  top: 0, left: 0, right: 0, bottom: 100,
                  child: DraggableScrollableSheet(
                    initialChildSize: 0.32,
                    minChildSize: 0.14,
                    maxChildSize: 0.85,
                    snap: true,
                    snapSizes: const [0.14, 0.32, 0.85],
                    builder: (context, scrollController) {
                      return Container(
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.only(
                              topLeft: Radius.circular(24),
                              topRight: Radius.circular(24)),
                          boxShadow: [
                            BoxShadow(
                                color: Colors.black26,
                                blurRadius: 12,
                                offset: Offset(0, -2))
                          ],
                        ),
                        child: _isLoadingRecommendations
                            ? const Center(child: CircularProgressIndicator())
                            : Column(
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                        vertical: 10),
                                    child: Container(
                                      width: 40, height: 4,
                                      decoration: BoxDecoration(
                                          color: Colors.grey.shade300,
                                          borderRadius:
                                              BorderRadius.circular(4)),
                                    ),
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 20),
                                    child: Row(
                                      children: [
                                        TX('추천 장소',
                                            style: const TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.bold)),
                                        Text(' ${_recommendedSpots.length}',
                                            style: const TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.bold)),
                                        const Spacer(),
                                        const Icon(Icons.filter_alt_outlined,
                                            size: 14, color: Colors.grey),
                                        const SizedBox(width: 2),
                                        TX('Ai 추천순',
                                            style: const TextStyle(
                                                fontSize: 11,
                                                color: Colors.grey)),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Expanded(
                                    child: _recommendedSpots.isEmpty
                                        ? Center(
                                            child: TX(
                                                '추천 장소가 없습니다. 잠시 후 다시 시도해주세요.',
                                                style: const TextStyle(
                                                    fontSize: 13,
                                                    color: Colors.grey)))
                                        : ListView.builder(
                                            controller: scrollController,
                                            padding:
                                                const EdgeInsets.symmetric(
                                                    horizontal: 16,
                                                    vertical: 8),
                                            itemCount:
                                                _recommendedSpots.length,
                                            itemBuilder: (context, index) {
                                              final spot =
                                                  _recommendedSpots[index];
                                              final isSelected =
                                                  _selectedSpotIndex == index;
                                              return GestureDetector(
                                                behavior:
                                                    HitTestBehavior.opaque,
                                                onTap: () =>
                                                    _onSpotChanged(index),
                                                child: _buildInfoCard(
                                                    spot, isSelected),
                                              );
                                            },
                                          ),
                                  ),
                                ],
                              ),
                      );
                    },
                  ),
                ),

                // 하단 활동 바
                Positioned(
                  bottom: 0, left: 0, right: 0,
                  child: Container(
                    height: 100,
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
                        final actName = widget.selectedActivities[index];
                        final isSelected = _currentIndex == index;
                        return GestureDetector(
                          onTap: () {
                            setState(() => _currentIndex = index);
                            _loadRecommendations();
                          },
                          child: Padding(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 16.0),
                            child: AnimatedOpacity(
                              duration: const Duration(milliseconds: 200),
                              opacity: isSelected ? 1.0 : 0.4,
                              child: Image.asset(
                                  'assets/icons/${_activityIcons[actName] ?? 'running.png'}',
                                  width: isSelected ? 50 : 40,
                                  height: isSelected ? 50 : 40),
                            ),
                          ),
                        );
                      }),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildInfoCard(Map<String, dynamic> spot, bool isSelected) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
            color: isSelected ? const Color(0xFF3A6FF8) : Colors.transparent,
            width: 2),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, 3))
        ],
      ),
      child: Row(
        children: [
          // 카카오 이미지 (없으면 아이콘)
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: spot['image'] != null
                ? Image.network(spot['image'],
                    width: 90, height: 90, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _imgFallback())
                : _imgFallback(),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _buildTag(spot['tags'][0]),
                    const SizedBox(width: 4),
                    _buildTag(spot['tags'][1], isGray: true),
                  ],
                ),
                const SizedBox(height: 8),
                Text('${spot['title']} (${spot['distance']})',
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.bold),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                Text(spot['desc'],
                    style: const TextStyle(
                        fontSize: 11, color: Colors.black87),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    TX('추천 점수',
                        style: const TextStyle(
                            fontSize: 11, fontWeight: FontWeight.bold)),
                    Text(spot['score'],
                        style: const TextStyle(
                            fontSize: 18,
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
      width: 90,
      height: 90,
      color: Colors.blue.shade50,
      child: const Icon(Icons.photo, color: Colors.blueAccent, size: 36));

  Widget _buildTag(String text, {bool isGray = false}) {
    if (text.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
          color: isGray ? Colors.grey.shade200 : Colors.blue.shade50,
          borderRadius: BorderRadius.circular(12)),
      child: TX(text,
          style: TextStyle(
              fontSize: 9,
              color: isGray ? Colors.black54 : Colors.blueAccent,
              fontWeight: FontWeight.bold)),
    );
  }
}
