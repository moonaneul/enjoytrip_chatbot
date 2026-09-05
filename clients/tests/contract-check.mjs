/* 개발자 2의 서버가 Shared API Contract를 지키는지 검사합니다.
 *
 *   node clients/tests/contract-check.mjs                    # http://127.0.0.1:8000
 *   node clients/tests/contract-check.mjs http://localhost:8000
 *
 * Node 18 이상이면 그대로 돕니다. 설치할 패키지가 없습니다.
 * [필수]는 프런트가 화면에 그리지 못하는 항목, [권고]는 화면은 나오지만 품질이 떨어지는 항목입니다.
 */
const base = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');

const LEVELS = ['COMFORTABLE', 'CHECK_NEEDED', 'BURDEN_POSSIBLE', 'INSUFFICIENT_DATA'];
const STATUS = ['SATISFIED', 'CONFLICT', 'UNKNOWN'];
const STATUS_ALIAS = ['UNSATISFIED', 'NOT_SATISFIED', 'CAUTION'];
const ERROR_CODES = ['PLACE_NOT_FOUND', 'AMBIGUOUS_PLACE'];
const ERROR_ALIAS = ['NOT_FOUND', 'PLACE_AMBIGUOUS', 'MULTIPLE_PLACES'];
const NEED_KEYS = [
  'walking_difficult', 'stairs_difficult', 'need_rest_area', 'wheelchair_needed',
  'restroom_important', 'stroller', 'need_nursing_room',
  'need_diaper_station', 'need_elevator'
];
// v2 12-1의 금지 표현. answer와 reason에 섞이면 화면 말투가 무너집니다.
const INTERNAL_UI_TERMS = /Rule Engine|Comfort 판정|SATISFIED|CONFLICT|UNKNOWN|CHECK_NEEDED|BURDEN_POSSIBLE|INSUFFICIENT_DATA|need_[A-Za-z_]+|stairs_difficult|walking_difficult|stroller\s*:/i;
const BANNED = /에 대해|에 관하여|로부터|을 통하여|를 통하여|제공됩니다|제공되고|지원합니다|가능합니다|확인할 수 있습니다|판단됩니다|요구됩니다|되어집니다|하실 수 있으십니다|귀하|당신|사용자님|고객님|해당 시설|본 서비스/;

const fails = [];
const warns = [];
const ok = message => console.log(`  OK    ${message}`);
const bad = message => { fails.push(message); console.log(`  FAIL  ${message}`); };
const warn = message => { warns.push(message); console.log(`  WARN  ${message}`); };
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isText = value => typeof value === 'string' && value.trim() !== '';

async function ask(body) {
  const response = await fetch(`${base}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const raw = await response.text();
  let data = null;
  try { data = JSON.parse(raw); } catch { /* 아래에서 보고합니다 */ }
  return { status: response.status, data, raw };
}

function checkTone(where, value) {
  if (!isText(value)) return;
  const hit = value.match(BANNED);
  if (hit) warn(`[권고] ${where}에 금지 표현 "${hit[0]}" — 해요체로 바꿔 주세요`);
  if (value.length > 120) warn(`[권고] ${where}가 ${value.length}자입니다. 두 문장 이내로 줄여 주세요`);
}

function checkSuccess(data, label) {
  console.log(`\n[${label}] 성공 응답 계약`);

  if (!isObject(data)) { bad('[필수] 응답이 JSON 객체가 아닙니다'); return null; }
  if (typeof data.success !== 'boolean') { bad('[필수] success가 boolean이 아닙니다. 프런트가 형식 오류로 처리합니다'); return null; }
  if (data.success === false) { bad(`[필수] 성공 응답을 기대했지만 success=false 입니다 (code: ${data.error?.code ?? '없음'})`); return null; }
  ok('success: true');

  if (isText(data.answer)) {
    ok('answer 있음'); checkTone('answer', data.answer);
    if (data.answer.length > 160) bad(`[필수] answer가 ${data.answer.length}자입니다. 사용자용 요약은 160자 이하로 제한해 주세요`);
    const internal = data.answer.match(INTERNAL_UI_TERMS);
    if (internal) bad(`[필수] answer에 내부 판정 표현 \"${internal[0]}\"이 노출됩니다`);
  } else bad('[필수] answer가 비어 있습니다. 카드 요약 자리에 들어갑니다');

  const place = data.place;
  if (!isObject(place)) bad('[필수] place가 객체가 아닙니다');
  else {
    if (isText(String(place.content_id ?? ''))) ok(`place.content_id: ${place.content_id}`);
    else bad('[필수] place.content_id가 없습니다. 후속 질문이 이어지지 않습니다');
    if (isText(place.name)) ok(`place.name: ${place.name}`); else bad('[필수] place.name이 없습니다');
    if (!isText(place.address)) warn('[권고] place.address가 없습니다. 카드에서 주소 줄이 사라집니다');
    if (!isText(place.region)) warn('[권고] place.region이 없습니다. 카드 머리말이 "전국 여행 정보"로 표시됩니다');
  }

  const comfort = data.comfort;
  if (!isObject(comfort)) bad('[필수] comfort가 객체가 아닙니다. 판정 띠를 그리지 못합니다');
  else {
    if (LEVELS.includes(comfort.level)) ok(`comfort.level: ${comfort.level}`);
    else bad(`[필수] comfort.level이 ${LEVELS.join(' / ')} 중 하나가 아닙니다 (받은 값: ${comfort.level})`);
    const items = Array.isArray(comfort.items) ? comfort.items : [];
    if (!items.length) warn('[권고] comfort.items가 비어 있습니다. 조건 결과 줄이 사라집니다');
    items.forEach((item, index) => {
      if (!isObject(item)) { bad(`[필수] comfort.items[${index}]가 객체가 아닙니다`); return; }
      if (STATUS.includes(item.status)) return;
      if (STATUS_ALIAS.includes(item.status)) warn(`[권고] comfort.items[${index}].status가 별칭 ${item.status} 입니다. ${STATUS.join(' / ')} 로 통일해 주세요`);
      else bad(`[필수] comfort.items[${index}].status가 ${STATUS.join(' / ')} 중 하나가 아닙니다 (받은 값: ${item.status})`);
    });
    items.forEach((item, index) => { if (isObject(item)) checkTone(`comfort.items[${index}].reason`, item.reason); });
    if (items.length) ok(`comfort.items ${items.length}개 (앞 3개가 카드에 바로 보입니다)`);
    if (items.length > 3) warn('[권고] 중요한 항목을 앞 3개에 담아 주세요. 나머지는 접힌 영역으로 내려갑니다');
  }

  const sections = Array.isArray(data.sections) ? data.sections : null;
  if (!sections) bad('[필수] sections가 배열이 아닙니다');
  else {
    sections.forEach((section, index) => {
      if (!isObject(section)) { bad(`[필수] sections[${index}]가 객체가 아닙니다`); return; }
      if (!isText(section.title)) warn(`[권고] sections[${index}].title이 없습니다. key로 대체 표시합니다`);
      (Array.isArray(section.items) ? section.items : []).forEach((item, at) => {
        if (!isObject(item)) { bad(`[필수] sections[${index}].items[${at}]가 객체가 아닙니다`); return; }
        if (typeof item.value !== 'string') bad(`[필수] sections[${index}].items[${at}].value는 화면 표시용 문자열이어야 합니다 (받은 타입: ${typeof item.value})`);
      });
    });
    ok(`sections ${sections.length}개`);
  }

  const facilities = Array.isArray(data.facilities) ? data.facilities : null;
  if (!facilities) bad('[필수] facilities가 배열이 아닙니다');
  else {
    facilities.forEach((facility, index) => {
      if (!isObject(facility)) { bad(`[필수] facilities[${index}]가 객체가 아닙니다`); return; }
      if (!isText(facility.name)) warn(`[권고] facilities[${index}].name이 없습니다. type으로 대체 표시합니다`);
      const search = facility.map_search_text;
      if (search === null || search === undefined || !isText(search)) {
        warn(`[권고] facilities[${index}].map_search_text가 없습니다. 지도 링크와 복사 버튼이 함께 사라집니다`);
      } else {
        if (isText(facility.location_detail) && search.includes(facility.location_detail)) {
          bad(`[필수] facilities[${index}].map_search_text에 내부 위치("${facility.location_detail}")가 섞였습니다. 지도에서 검색되지 않습니다`);
        }
        if (isText(facility.address) && !search.includes(facility.address.split(' ')[0])) {
          warn(`[권고] facilities[${index}].map_search_text에 주소가 빠진 것 같습니다: "${search}"`);
        }
      }
      if (!isText(facility.type)) warn(`[권고] facilities[${index}].type이 없습니다. 기본 핀 아이콘으로 그립니다`);
    });
    ok(`facilities ${facilities.length}개`);
    if (facilities.length > 5) warn('[권고] facilities는 관련도 높은 순으로 5개까지가 적당합니다');
  }

  const unknown = Array.isArray(data.unknown_fields) ? data.unknown_fields : null;
  if (!unknown) bad('[필수] unknown_fields가 배열이 아닙니다');
  else if (unknown.some(key => typeof key !== 'string')) bad('[필수] unknown_fields는 문자열 배열이어야 합니다');
  else ok(`unknown_fields ${unknown.length}개`);

  const sources = Array.isArray(data.sources) ? data.sources : null;
  if (!sources) bad('[필수] sources가 배열이 아닙니다');
  else if (!sources.length) warn('[권고] sources가 비어 있습니다. 출처 없는 사실 정보는 표시하지 않는 것이 원칙입니다');
  else ok(`sources ${sources.length}개`);

  const suggested = Array.isArray(data.suggested_questions) ? data.suggested_questions : null;
  if (!suggested) bad('[필수] suggested_questions가 배열이 아닙니다');
  else {
    if (suggested.some(question => typeof question !== 'string')) bad('[필수] suggested_questions는 문자열 배열이어야 합니다');
    else ok(`suggested_questions ${suggested.length}개`);
    if (suggested.length > 3) warn('[권고] 추천 질문은 3개까지만 화면에 붙습니다');
  }

  return isObject(place) ? String(place.content_id ?? '') : null;
}

function checkFailure(data, label) {
  console.log(`\n[${label}] 실패 응답 계약`);
  if (!isObject(data) || typeof data.success !== 'boolean') { bad('[필수] success가 boolean이 아닙니다'); return; }
  if (data.success !== false) { warn('[권고] 없는 장소인데 success=true 입니다. 지어낸 답이 아닌지 확인해 주세요'); return; }
  ok('success: false');
  const code = data.error?.code;
  if (ERROR_CODES.includes(code)) ok(`error.code: ${code}`);
  else if (ERROR_ALIAS.includes(code)) warn(`[권고] error.code가 별칭 ${code} 입니다. ${ERROR_CODES.join(' / ')} 로 통일해 주세요`);
  else warn(`[권고] error.code가 ${code ?? '없음'} 입니다. 장소를 못 찾은 경우 PLACE_NOT_FOUND를 주면 화면이 지역 재입력을 안내합니다`);
  if (!isText(data.answer) && !isText(data.error?.message)) bad('[필수] answer와 error.message가 모두 비어 있어 사용자에게 보여줄 문장이 없습니다');
  else ok('사용자에게 보여줄 문장 있음');
  checkTone('실패 answer', data.answer);
}

(async () => {
  console.log(`온가 · Shared API Contract 검사\n대상: ${base}/chat\n`);

  let first;
  try {
    first = await ask({
      message: '엄마랑 경복궁 가려고 하는데 계단이 힘들어.',
      traveler_type: 'senior',
      needs: ['stairs_difficult', 'need_rest_area', 'restroom_important'],
      current_place_id: null
    });
  } catch (error) {
    console.log(`\n서버에 연결하지 못했습니다: ${error.message}`);
    console.log('개발자 2의 FastAPI를 먼저 띄운 뒤 다시 실행해 주세요.\n');
    process.exit(2);
  }

  console.log('[요청] 프런트가 실제로 보내는 형태');
  console.log('  { message, traveler_type, needs, current_place_id }  ← use_rag를 보내지 않습니다');
  if (first.status === 200) ok('HTTP 200');
  else bad(`[필수] HTTP ${first.status} 입니다. 프런트는 200이 아니면 오류 카드를 띄웁니다`);
  if (first.data === null) {
    bad('[필수] 응답이 JSON이 아닙니다');
    console.log(`  받은 본문 앞부분: ${first.raw.slice(0, 160)}`);
  }
  if (first.data && !('success' in first.data) && 'answer' in first.data && 'source' in first.data) {
    console.log('\n  ※ 아직 예전 {answer, source} 형식입니다. 여행 계약으로 교체가 필요합니다.');
  }

  const placeId = first.data ? checkSuccess(first.data, '1차 질문') : null;

  if (placeId) {
    const followUp = await ask({
      message: '화장실 위치 알려줘',
      traveler_type: 'senior',
      needs: ['restroom_important'],
      current_place_id: placeId
    });
    console.log(`\n[후속 질문] current_place_id="${placeId}" 로 이어서 질문`);
    if (followUp.status === 200 && isObject(followUp.data)) {
      const sameOrNew = String(followUp.data.place?.content_id ?? '');
      if (sameOrNew === placeId) ok('같은 장소를 유지했습니다');
      else warn(`[권고] 장소가 ${sameOrNew || '없음'} 으로 바뀌었습니다. 장소명이 없는 질문은 기존 ID를 유지해 주세요`);
      checkSuccess(followUp.data, '후속 질문');
    } else bad(`[필수] 후속 질문이 HTTP ${followUp.status} 입니다`);
  }

  const missing = await ask({
    message: '없는관광지12345 계단 많아?',
    traveler_type: 'both',
    needs: [],
    current_place_id: null
  });
  if (missing.status === 200 && isObject(missing.data)) checkFailure(missing.data, '없는 장소');
  else bad(`[필수] 없는 장소 질문이 HTTP ${missing.status} 입니다. 업무 오류도 200 + success:false 로 주세요`);

  console.log('\n[참고] needs로 보낼 수 있는 값');
  console.log(`  ${NEED_KEYS.join(', ')}`);

  console.log(`\n────────────────────────────────`);
  console.log(`필수 위반 ${fails.length}건 · 권고 ${warns.length}건`);
  if (fails.length) {
    console.log('\n먼저 고쳐야 할 것:');
    fails.forEach(message => console.log(`  · ${message}`));
  }
  if (!fails.length) console.log('계약을 지키고 있습니다. 프런트와 그대로 붙일 수 있습니다.');
  console.log('');
  process.exit(fails.length ? 1 : 0);
})();
