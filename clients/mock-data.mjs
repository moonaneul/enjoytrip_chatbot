/** UI fixtures only: every place/facility description below is fictional test data.
 * Loaded exclusively when an explicit ?mock=... query is present. Never a network fallback.
 */
const source = [{ organization: '화면 테스트용 기관', title: '가상 무장애 여행 정보 · 실제 자료 아님', updated_at: '2026-09-04' }];
const palace = { content_id: 'mock-palace', name: '경복궁 (화면 예시)', address: '서울특별시 종로구 사직로 161', region: '서울특별시' };
const museum = { content_id: 'mock-museum', name: '국립중앙박물관 (화면 예시)', address: '서울특별시 용산구 서빙고로 137', region: '서울특별시' };
const facility = (type, name, place, location) => ({ type, name, parent_place: place.name, address: place.address, location_detail: location, map_search_text: `${place.name} ${place.address}` });
const base = {
  success: true, answer: '예시 응답: 부모님과 방문할 때 이동 경로와 보행거리를 미리 확인해 주세요.',
  place: palace,
  comfort: { level: 'CHECK_NEEDED', label: '방문 전 확인할 정보가 있어요', items: [
    { need: 'need_rest_area', status: 'SATISFIED', reason: '예시 자료에 쉴 곳이 안내되어 있어요.' },
    { need: 'walking_difficult', status: 'UNKNOWN', reason: '전체 보행거리 정보를 확인하지 못했어요.' }
  ] },
  sections: [
    { key: 'mobility', title: '이동 정보', items: [{ label: '계단·경사', value: '예시: 일부 구간의 우회 경로 확인 필요' }, { label: '보행거리', value: '미확인' }] },
    { key: 'senior', title: '부모님 정보', items: [{ label: '휴식공간', value: '예시: 안내소 주변 쉼터' }, { label: '휠체어 대여', value: '대여 가능 여부 미확인' }] }
  ],
  facilities: [facility('restroom', '화장실', palace, '예시: 입구 안내소 옆')],
  unknown_fields: ['걷기 부담', '휠체어 이동'], sources: source,
  suggested_questions: ['화장실 위치 알려줘', '많이 걸어야 하는지 알려줘']
};
export const MOCK_RESPONSES = {
  senior: base,
  baby: {
    ...base, answer: '예시 응답: 유모차 이동과 돌봄 시설 정보를 함께 확인했어요.', place: museum,
    comfort: { level: 'COMFORTABLE', label: '편안하게 이용할 가능성이 높아요', items: [
      { need: 'need_elevator', status: 'SATISFIED', reason: '예시 자료에 엘리베이터가 안내되어 있어요.' },
      { need: 'need_nursing_room', status: 'SATISFIED', reason: '예시 자료에 수유실 위치가 안내되어 있어요.' }
    ] },
    sections: [
      { key: 'mobility', title: '이동 정보', items: [{ label: '유모차', value: '예시: 엘리베이터를 이용한 실내 이동' }] },
      { key: 'baby', title: '아이 정보', items: [{ label: '수유실', value: '예시: 어린이박물관 1층' }, { label: '기저귀 교환시설', value: '예시: 가족 휴게실' }] },
      { key: 'amenities', title: '편의시설', items: [{ label: '주차', value: '주차 후 이동 경로는 방문 전 확인해 주세요.' }] }
    ],
    facilities: [facility('nursing_room', '수유실', museum, '예시: 어린이박물관 1층'), facility('diaper_station', '기저귀 교환시설', museum, '예시: 가족 휴게실'), facility('restroom', '화장실', museum, '예시: 안내데스크 옆')],
    unknown_fields: [], suggested_questions: ['수유실 위치 알려줘', '주차 후 유모차 이동 경로 알려줘']
  },
  both: {
    ...base, answer: '예시 응답: 부모님과 아이가 함께 이동할 경로와 돌봄 공간을 미리 확인해 주세요.',
    sections: [...base.sections, { key: 'baby', title: '아이 정보', items: [{ label: '유모차 이동', value: '노면 상태 미확인' }, { label: '수유실', value: '미확인' }] }],
    facilities: [facility('restroom', '화장실', palace, '예시: 입구 안내소 옆'), facility('rest_area', '휴식공간', palace, '예시: 안내소 앞')],
    unknown_fields: ['걷기 부담', '경사', '수유실', '기저귀 교환'],
    suggested_questions: ['쉬는 곳이랑 수유실 둘 다 확인해줘', '우리 가족의 이동 경로 확인해줘']
  },
  burden: {
    ...base, answer: '예시 응답: 계단 이용이 어려운 가족에게 일부 구간은 부담이 있을 수 있어요.',
    comfort: { level: 'BURDEN_POSSIBLE', label: '현재 조건에서는 부담이 있을 수 있어요', items: [{ need: 'stairs_difficult', status: 'CONFLICT', reason: '예시 자료에 계단이 포함된 구간이 있어요.' }] },
    facilities: []
  },
  insufficient: {
    ...base, answer: '예시 응답: 현재 자료만으로는 가족의 이용 편의성을 판단하기 어려워요.',
    comfort: { level: 'INSUFFICIENT_DATA', label: '판단할 정보가 부족해요', items: [{ need: 'walking_difficult', status: 'UNKNOWN', reason: '보행거리 자료 미확인' }, { need: 'need_elevator', status: 'UNKNOWN', reason: '엘리베이터 자료 미확인' }] },
    sections: [], facilities: [], unknown_fields: ['걷기 부담', '엘리베이터', '수유실', '기저귀 교환'], suggested_questions: []
  },
  many: {
    ...base, answer: '예시 응답: 이동 중에 들를 만한 시설을 정리했어요.',
    facilities: [
      facility('restroom', '화장실', palace, '예시: 입구 안내소 옆'),
      facility('rest_area', '쉼터', palace, '예시: 안내소 앞'),
      facility('parking', '주차장', palace, '예시: 주차장 2'),
      facility('nursing_room', '수유실', palace, '예시: 관리사무소 1층')
    ]
  },
  no_address: { ...base, facilities: [{ ...facility('restroom', '화장실', palace, '예시: 입구 옆'), address: null }] },
  no_map: { ...base, facilities: [{ ...facility('restroom', '화장실', palace, '예시: 입구 옆'), map_search_text: null }, { ...facility('rest_area', '쉼터', palace, null), map_search_text: '   ' }] },
  not_found: { success: false, answer: '관광지를 찾지 못했어요. 이름과 지역을 다시 알려주세요.', error: { code: 'PLACE_NOT_FOUND', message: '관광지 검색 결과 없음' } },
  ambiguous: { success: false, answer: '검색된 관련 장소가 여러 곳 있어 정확한 장소를 확인해야 해요.', error: { code: 'AMBIGUOUS_PLACE', message: 'Multiple places matched the supplied name.' }, candidates: [{ content_id: 'mock-haeundae-beach', name: '해운대해수욕장', address: '부산광역시 해운대구 해운대해변로 264', region: '부산광역시 해운대구' }, { content_id: 'mock-haeundae-zone', name: '해운대 관광특구', address: '부산광역시 해운대구', region: '부산광역시 해운대구' }] },
  failure: { success: false, answer: '지금은 여행 정보를 가져오기 어려워요. 잠시 후 다시 질문해 주세요.', error: { code: 'DATA_UNAVAILABLE', message: '자료 조회 실패' } }
};

export async function getMockResponse(name, request, signal) {
  await new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new DOMException('Aborted', 'AbortError')); return; }
    const abort = () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, name === 'slow' ? 12000 : name === 'timeout' ? 60000 : 650);
    signal.addEventListener('abort', abort, { once: true });
  });
  if (name === 'network') throw new TypeError('Failed to fetch');
  if (name === 'http_error') throw new Error('HTTP_503');
  let scenario = name;
  if (['auto', 'slow', 'timeout'].includes(name)) {
    scenario = request.traveler_type;
    if (request.message.includes('국립중앙박물관')) scenario = 'baby';
    else if (request.message.includes('경복궁')) scenario = 'senior';
    else if (request.current_place_id === 'mock-museum') scenario = 'baby';
    else if (request.current_place_id === 'mock-palace') scenario = 'senior';
    else if (request.current_place_id === 'mock-haeundae-beach' || request.current_place_id === 'mock-haeundae-zone') scenario = request.traveler_type || 'both';
  }
  if (!MOCK_RESPONSES[scenario]) throw new Error('INVALID_RESPONSE');
  return structuredClone(MOCK_RESPONSES[scenario]);
}
