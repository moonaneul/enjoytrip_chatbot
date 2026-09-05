/* 온가 integrated v3. Backend v11 contract + concise structured UI. Raw success answer는 화면에 직접 노출하지 않습니다. */
(() => {
  'use strict';

  const APP_BUILD = 'integrated-v3';
  document.documentElement.dataset.build = APP_BUILD;
  console.info(`[ON-GA] ${APP_BUILD}`);

  // ── 조건 ──────────────────────────────────────────────────────────
  const NEEDS = {
    walking_difficult: '오래 걷기 어려워요', stairs_difficult: '계단이 힘들어요',
    need_rest_area: '자주 쉬어야 해요', wheelchair_needed: '휠체어가 필요할 수 있어요',
    restroom_important: '화장실 접근이 중요해요',
    stroller: '유모차를 사용해요', need_nursing_room: '수유실이 필요해요',
    need_diaper_station: '기저귀 교환시설이 필요해요', need_elevator: '엘리베이터가 필요해요'
  };
  const SHORT = {
    walking_difficult: '걷기', stairs_difficult: '계단', need_rest_area: '휴식',
    wheelchair_needed: '휠체어', restroom_important: '화장실',
    stroller: '유모차', need_nursing_room: '수유실', need_diaper_station: '기저귀', need_elevator: '엘리베이터'
  };
  const FAMILY_NEEDS = {
    senior: ['walking_difficult', 'stairs_difficult', 'need_rest_area', 'wheelchair_needed', 'restroom_important'],
    baby: ['stroller', 'need_nursing_room', 'need_diaper_station', 'need_elevator', 'need_rest_area']
  };
  FAMILY_NEEDS.both = [...new Set([...FAMILY_NEEDS.senior, ...FAMILY_NEEDS.baby])];
  // 한 화면에 최대 6개. both의 나머지는 '더보기'로 접어 둡니다.
  const PRIMARY_NEEDS = {
    senior: FAMILY_NEEDS.senior, baby: FAMILY_NEEDS.baby,
    both: ['stairs_difficult', 'need_rest_area', 'restroom_important', 'stroller', 'need_nursing_room', 'need_elevator']
  };
  // 아무것도 고르지 않아도 이 값이 전송됩니다.
  const DEFAULT_NEEDS = {
    senior: ['stairs_difficult', 'need_rest_area', 'restroom_important'],
    baby: ['stroller', 'need_nursing_room', 'need_diaper_station'],
    both: ['stairs_difficult', 'need_rest_area', 'restroom_important', 'stroller', 'need_nursing_room']
  };
  const FAMILY_LABELS = { senior: '부모님과 함께', baby: '아이와 함께', both: '부모님과 아이 모두' };
  const FAMILY_SHORT = { senior: '부모님과', baby: '아이와', both: '다 같이' };
  const QUESTIONS = {
    senior: ['많이 걸어야 해?', '계단이나 경사가 많아?', '중간에 쉴 곳 있어?', '휠체어 빌릴 수 있어?', '화장실 이용하기 편해?'],
    baby: ['유모차로 다닐 수 있어?', '수유실 있어?', '기저귀 갈 곳 있어?', '엘리베이터 있어?', '주차 후 이동하기 편해?'],
    both: ['우리 가족 모두 이용하기 편할까?', '많이 걷거나 계단 오를 일이 있어?', '쉬거나 아이 돌볼 곳 있어?', '화장실과 수유시설 확인해줘']
  };
  // 되묻기용 힌트. 사용자가 칩으로 확인해 주기 전까지 유형을 확정하지 않습니다.
  const HINTS = {
    senior: ['엄마', '어머니', '아버지', '아빠', '부모님', '할머니', '할아버지', '어르신', '노모', '장인', '장모', '70대', '80대', '휠체어'],
    baby: ['아기', '아이', '애기', '유모차', '수유', '기저귀', '돌쟁이', '두 살', '세 살', '유아', '영유아', '아들', '딸']
  };

  // ── 표시 ──────────────────────────────────────────────────────────
  // 라벨과 색은 backend enum만 따릅니다. 답변 문장이나 선택 조건으로 등급을 바꾸지 않습니다.
  const COMFORT = {
    COMFORTABLE: ['편안하게 이용할 가능성이 높아요', '편안하게'],
    CHECK_NEEDED: ['방문 전 확인할 정보가 있어요', '확인할 정보가'],
    BURDEN_POSSIBLE: ['현재 조건에서는 부담이 있을 수 있어요', '부담이'],
    INSUFFICIENT_DATA: ['판단할 정보가 부족해요', '정보가 부족해요']
  };
  // 온이 표정. 판정 4종과 1:1로 이어지며, 문구는 항상 함께 나갑니다.
  const FACE = {
    COMFORTABLE: '<circle cx="14" cy="17.5" r="1.9" class="eye"/><circle cx="26" cy="17.5" r="1.9" class="eye"/><path class="mouth" d="M13.5 24.5c2.6 3.2 10.4 3.2 13 0"/>',
    CHECK_NEEDED: '<path class="brow" d="M10.4 12.6c1.8-1.4 3.8-1.4 5.4 0"/><circle cx="13" cy="18.2" r="1.9" class="eye"/><circle cx="26" cy="18.2" r="1.9" class="eye"/><path class="mouth" d="M13.8 25.8c2.8 1.6 7.4 1 10-1.8"/>',
    BURDEN_POSSIBLE: '<circle cx="14" cy="17.5" r="1.9" class="eye"/><circle cx="26" cy="17.5" r="1.9" class="eye"/><path class="mouth" d="M13.5 26.8c2.6-3.2 10.4-3.2 13 0"/>',
    INSUFFICIENT_DATA: '<circle cx="14" cy="18" r="1.9" class="eye"/><circle cx="26" cy="18" r="1.9" class="eye"/><path class="mouth" d="M14.2 25.4h11.6"/><path class="mark" d="M33.4 9.6c1.7-1.4 4-.2 3.7 1.8-.2 1.4-1.7 1.6-1.9 2.9"/><circle cx="35.1" cy="17" r="1.1" class="eye"/>'
  };
  FACE.UNRECOGNIZED = FACE.INSUFFICIENT_DATA;
  const CHECK_MARK = '<path d="M3 8.6l3.6 4L13 3.4"/>';
  const STATUS = {
    SATISFIED: ['✓', '확인'], CONFLICT: ['!', '조건 미충족'], UNKNOWN: ['?', '미확인'],
    UNSATISFIED: ['!', '조건 미충족'], NOT_SATISFIED: ['!', '조건 미충족'], CAUTION: ['!', '주의']
  };
  const STATUS_REASON = {
    SATISFIED: '공식 정보에서 확인됐어요.',
    CONFLICT: '현재 조건에서는 이용이 불편할 수 있어요.',
    UNKNOWN: '공식 자료에서 아직 확인되지 않았어요.'
  };
  const FIELD_LABELS = {
    walking_distance: '걷는 거리', slope: '경사', stairs: '계단', elevator: '엘리베이터',
    wheelchair: '휠체어', wheelchair_rental: '휠체어 대여', stroller: '유모차 이동',
    nursing_room: '수유실', diaper_station: '기저귀 교환시설', restroom: '화장실',
    rest_area: '쉴 곳', parking: '주차', parking_access: '주차 후 이동 경로',
    walking_difficult: '걷기 부담', stairs_difficult: '계단', need_rest_area: '쉴 곳',
    wheelchair_needed: '휠체어', restroom_important: '화장실',
    need_nursing_room: '수유실', need_diaper_station: '기저귀 교환시설', need_elevator: '엘리베이터'
  };
  const SECTION_TITLES = { mobility: '이동', senior: '부모님', baby: '아이', amenities: '편의시설', basic: '기본 정보' };
  const COPY = {
    loading1: '공식 자료를 찾고 있어요…',
    loading2: '우리 가족 조건이랑 맞춰보고 있어요…',
    loading3: '조금 오래 걸리네요. 거의 다 됐어요…',
    empty: '어디를 가시는지 알려주세요.',
    unknown: '아래 정보는 공식 자료에 안 나와 있어요.',
    copyDone: '✓ 복사했어요',
    copyFail: '자동 복사가 안 되네요. 아래 주소를 직접 복사해 주세요.',
    noAddress: '주소는 아직 확인된 자료가 없어요.',
    applied: '다음 질문부터 반영할게요.',
    retry: '다시 시도'
  };

  // ── 지도 딥링크 ───────────────────────────────────────────────────
  // 지도 SDK를 쓰지 않습니다. 인증키도 좌표도 없습니다. 서버가 준 검색 문자열만 URL로 감쌉니다.
  const MAPS = {
    kakao: ['카카오맵', query => `https://map.kakao.com/link/search/${query}`],
    naver: ['네이버지도', query => `https://map.naver.com/p/search/${query}`],
    google: ['구글지도', query => `https://www.google.com/maps/search/?api=1&query=${query}`]
  };
  const MAP_ORDER = ['kakao', 'naver', 'google'];

  // 시설 종류 픽토그램. 아래 문자열은 전부 이 파일의 상수이며 서버 데이터가 섞이지 않습니다.
  const PICTO = {
    restroom: '<path d="M5 2.5h14v19H5z"/><circle cx="15.5" cy="12" r="1.2"/>',
    nursing_room: '<path d="M10 2.5h4v3h-4z"/><path d="M8.8 5.5h6.4v13a3 3 0 0 1-3 3h-.4a3 3 0 0 1-3-3z"/><path d="M8.8 11h6.4"/>',
    diaper_station: '<path d="M3 6.5h18v3.5a9 9 0 0 1-18 0z"/><path d="M8 17.5h8"/>',
    parking: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M9.5 17V7.5h3.2a2.9 2.9 0 0 1 0 5.8H9.5"/>',
    rest_area: '<path d="M3 6.5h18M3 11.5h18M5 11.5V19M19 11.5V19"/>',
    elevator: '<rect x="4" y="2.5" width="16" height="19" rx="2"/><path d="M9.2 11V7m0 0L7.7 8.6M9.2 7l1.6 1.6M14.8 13v4m0 0l1.6-1.6M14.8 17l-1.6-1.6"/>',
    default: '<path d="M12 21.5s7-6.4 7-11.5a7 7 0 1 0-14 0c0 5.1 7 11.5 7 11.5z"/><circle cx="12" cy="10" r="2.6"/>'
  };

  // ── 도구 ──────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  const text = value => typeof value === 'string' ? value.trim() : typeof value === 'number' ? String(value) : '';
  const list = value => Array.isArray(value) ? value : [];
  const object = value => value && typeof value === 'object' && !Array.isArray(value);
  const node = (tag, className, content) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = content;
    return element;
  };
  const announce = message => { $('sr-live').textContent = message; };

  const state = {
    travelerType: null, needs: new Set(), needsTouched: false, moreOpen: false,
    currentPlaceId: null, placeName: '', turns: 0, unknownCount: 0,
    suggested: [], answers: 0, mapApp: 'kakao',
    busy: false, controller: null, active: null,
    pending: null, queued: null, deferred: null, interrupting: false,
    confirmTurn: null, contextLine: null, onboardingTurn: null
  };
  const apiBase = (document.querySelector('meta[name="chat-api-base"]')?.content || '').replace(/\/$/, '');
  const mockCase = new URLSearchParams(location.search).get('mock');
  const timeoutMs = 45000;
  if (mockCase) $('mock-notice').hidden = false;

  // ── 지난번 기억 ───────────────────────────────────────────────────
  const STORE_KEY = 'onga.profile.v1';
  const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;

  const LEGACY_NEED_MAP = { long_walk_difficult: 'walking_difficult' };
  const VALID_NEEDS = new Set(Object.keys(NEEDS));
  function migrateStoredNeeds(value) {
    return [...new Set(list(value)
      .map(key => LEGACY_NEED_MAP[key] || key)
      .filter(key => typeof key === 'string' && VALID_NEEDS.has(key)))];
  }

  function loadProfile() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
      if (!object(saved) || !FAMILY_NEEDS[saved.travelerType]) return null;
      const savedAt = Date.parse(saved.savedAt);
      if (!Number.isFinite(savedAt) || Date.now() - savedAt > THIRTY_DAYS) return null;
      const needs = migrateStoredNeeds(saved.needs);
      // v5의 long_walk_difficult는 walking_difficult로 옮기고, 더 이상 계약에 없는 driving은 제거합니다.
      return { ...saved, needs };
    } catch { return null; }
  }
  function saveProfile() {
    // 질문 내용은 저장하지 않습니다. 유형·조건·선호 지도만 남깁니다.
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        travelerType: state.travelerType,
        needs: [...state.needs],
        mapApp: state.mapApp,
        savedAt: new Date().toISOString()
      }));
    } catch { /* 저장이 막힌 환경에서는 첫 방문처럼 동작합니다. */ }
  }

  // ── 대화 줄 만들기 ────────────────────────────────────────────────
  function chipRow(chips) {
    const row = node('div', 'chip-row');
    chips.filter(Boolean).forEach(([label, onClick]) => {
      const button = node('button', 'pick', label);
      button.type = 'button';
      button.addEventListener('click', () => onClick(button));
      row.append(button);
    });
    return row;
  }

  function botTurn(lines, chips, className = '') {
    const turn = node('div', `turn bot ${className}`.trim());
    const body = node('div', 'turn-body');
    lines.filter(Boolean).forEach(line => body.append(node('p', '', line)));
    if (chips?.length) body.append(chipRow(chips));
    turn.append(body);
    $('chat-window').append(turn);
    return turn;
  }

  function userTurn(message) {
    const turn = node('div', 'turn user');
    turn.append(node('div', 'bubble', message));
    $('chat-window').append(turn);
  }

  function systemLine(label, action) {
    const line = node('div', 'context-line');
    line.append(node('span', '', label));
    if (action) {
      const button = node('button', 'link-button', action[0]);
      button.type = 'button';
      button.addEventListener('click', action[1]);
      line.append(button);
    }
    $('chat-window').append(line);
    return line;
  }

  function scrollToLatest() {
    // 안내 줄이 아니라 실제 대화 내용이 화면 위에 오도록 합니다.
    const latest = [...$('chat-window').children].reverse().find(element => element.matches('.sheet, .turn'));
    if (!latest) return;
    const top = latest.getBoundingClientRect().top + window.scrollY - 76;
    window.scrollTo({ top: Math.max(0, top), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }

  // ── 가족 유형과 조건 ──────────────────────────────────────────────
  function summaryText() {
    const picked = [...state.needs].filter(key => FAMILY_NEEDS[state.travelerType]?.includes(key)).map(key => SHORT[key]);
    return `${FAMILY_LABELS[state.travelerType]} · ${picked.length ? picked.join(', ') : '조건 없음'}`;
  }

  function renderDrawer() {
    const family = $('family-options');
    family.replaceChildren();
    Object.keys(FAMILY_LABELS).forEach(type => {
      const label = node('label', 'chip');
      const input = node('input');
      input.type = 'radio'; input.name = 'traveler'; input.value = type; input.checked = state.travelerType === type;
      input.addEventListener('change', () => applyFamily(type));
      const box = node('span', 'box');
      box.append(svgNode('', '0 0 16 16', CHECK_MARK));
      label.append(input, box, node('span', '', FAMILY_LABELS[type]));
      family.append(label);
    });

    const wrap = $('needs-options');
    wrap.replaceChildren();
    if (!state.travelerType) return;
    const all = FAMILY_NEEDS[state.travelerType];
    const primary = PRIMARY_NEEDS[state.travelerType];
    const hidden = all.filter(key => !primary.includes(key));
    (state.moreOpen ? all : primary).forEach(key => {
      const label = node('label', 'chip');
      const input = node('input');
      input.type = 'checkbox'; input.value = key; input.checked = state.needs.has(key);
      input.addEventListener('change', () => {
        state.needsTouched = true;
        input.checked ? state.needs.add(key) : state.needs.delete(key);
        $('condition-summary').textContent = summaryText();
        state.suggested = []; renderQuickActions(); saveProfile();
      });
      const box = node('span', 'box');
      box.append(svgNode('', '0 0 16 16', CHECK_MARK));
      label.append(input, box, node('span', '', NEEDS[key]));
      wrap.append(label);
    });
    const more = $('needs-more');
    more.hidden = !hidden.length;
    more.textContent = state.moreOpen ? '접기' : `+ 더보기 (${hidden.length})`;
  }

  function applyFamily(type, keepNeeds) {
    if (!FAMILY_NEEDS[type]) return;
    const changed = state.travelerType !== type;
    state.travelerType = type;
    if (keepNeeds) state.needs = new Set(keepNeeds.filter(key => FAMILY_NEEDS[type].includes(key)));
    else if (state.needsTouched) state.needs = new Set([...state.needs].filter(key => FAMILY_NEEDS[type].includes(key)));
    else state.needs = new Set(DEFAULT_NEEDS[type]);
    if (changed) { state.moreOpen = false; state.suggested = []; }
    $('condition-bar').hidden = false;
    $('condition-summary').textContent = summaryText();
    $('form-feedback').textContent = '';
    renderDrawer(); renderQuickActions(); saveProfile();
  }

  function toggleDrawer(open) {
    const drawer = $('needs-drawer');
    const next = open ?? drawer.hidden;
    drawer.hidden = !next;
    $('condition-toggle').setAttribute('aria-expanded', String(next));
    if (next) { renderDrawer(); drawer.querySelector('input')?.focus(); }
  }

  // ── 추천 질문 ─────────────────────────────────────────────────────
  function questionChip(question, placeId) {
    return [question, () => {
      if (placeId) submitQuestion(question, placeId);
      else { $('user-input').value = question; $('user-input').focus(); announce('가시려는 곳 이름을 함께 적어주세요.'); }
    }];
  }

  function renderQuickActions() {
    // 추천 질문은 각 결과 카드의 하단에만 둡니다.
    // Sticky 입력창 위 칩이 새 질문으로 교체되어 보이던 문제를 제거합니다.
    $('quick-actions').replaceChildren();
  }

  // ── 장소 이어가기와 마무리 ────────────────────────────────────────
  function closePlace(manual) {
    if (!state.currentPlaceId) return;
    const name = state.placeName || '이 장소';
    state.contextLine?.querySelector('.link-button')?.remove();
    if (manual) {
      const divider = node('div', 'divider');
      divider.append(node('span', '', `${name} 이야기는 여기까지예요. 다음은 어디로 가볼까요?`));
      $('chat-window').append(divider);
    }
    if (state.turns >= 3) {
      const note = state.unknownCount ? `${name} (확인 필요 ${state.unknownCount}가지)` : name;
      $('chat-window').append(node('p', 'visit-summary note', `오늘 살펴본 곳 · ${note}`));
    }
    state.currentPlaceId = null; state.placeName = ''; state.turns = 0; state.unknownCount = 0;
    state.contextLine = null; state.suggested = [];
    renderQuickActions();
  }

  function updateContext(place) {
    const id = object(place) ? text(place.content_id) || null : null;
    const name = id ? text(place.name) : '';
    if (id && id !== state.currentPlaceId) {
      state.contextLine?.remove();
      state.currentPlaceId = id; state.placeName = name; state.turns = 0;
      state.contextLine = systemLine(`지금 ${name || '이 장소'} 이야기를 하고 있어요`, ['다른 곳 보기', () => {
        closePlace(true); $('user-input').focus();
      }]);
    } else if (id && state.contextLine) {
      // 같은 장소를 이어가는 중에는 안내 줄을 늘 최신 답변 아래에 둡니다.
      $('chat-window').append(state.contextLine);
    } else if (!id) {
      state.contextLine?.remove(); state.contextLine = null;
      state.currentPlaceId = null; state.placeName = ''; state.turns = 0;
    }
  }

  // ── 답변 카드 ─────────────────────────────────────────────────────
  function ruleLabel(label) { return node('p', 'rule-label', label); }

  function appendPair(dl, label, value) {
    if (!text(value)) return;
    const pair = node('div');
    pair.append(node('dt', '', label), node('dd', '', text(value)));
    dl.append(pair);
  }

  function svgNode(className, viewBox, inner) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', viewBox);
    svg.setAttribute('aria-hidden', 'true');
    if (className) svg.setAttribute('class', className);
    svg.innerHTML = inner;   // 이 파일의 상수만 넣습니다. 서버 문자열이 섞이지 않습니다.
    return svg;
  }

  function oniFace(level) {
    return svgNode('oni', '0 0 44 40', '<circle cx="20" cy="20" r="17" class="face"/>' + (FACE[level] || FACE.UNRECOGNIZED));
  }

  // 형광펜은 낱말 하나에만 칠합니다. 문구 자체는 그대로 둡니다.
  function markedText(label, keyword) {
    const fragment = document.createDocumentFragment();
    const at = keyword ? label.indexOf(keyword) : -1;
    if (at < 0) { fragment.append(document.createTextNode(label)); return fragment; }
    fragment.append(document.createTextNode(label.slice(0, at)));
    fragment.append(node('span', 'marker', keyword));
    fragment.append(document.createTextNode(label.slice(at + keyword.length)));
    return fragment;
  }

  function picto(type) {
    return svgNode('', '0 0 24 24', PICTO[type] || PICTO.default);
  }

  async function copySearch(search, card, button) {
    let copied = false;
    try {
      if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(search); copied = true; }
    } catch { /* 제한된 환경에서는 아래 textarea 방식으로 넘어갑니다. */ }
    if (!copied) {
      const helper = node('textarea');
      helper.value = search; helper.readOnly = true;
      helper.style.cssText = 'position:fixed;left:0;top:0;opacity:0;pointer-events:none';
      document.body.append(helper); helper.focus(); helper.select(); helper.setSelectionRange(0, search.length);
      try { copied = document.execCommand('copy'); } catch { copied = false; }
      helper.remove(); button.focus({ preventScroll: true });
    }
    if (copied) {
      card.querySelector('.manual-copy')?.remove();
      card.querySelector('.copy-feedback')?.remove();
      button.textContent = COPY.copyDone;
      button.classList.add('copied');
      announce('지도 검색어를 복사했어요.');
      clearTimeout(button.dataset.timer);
      button.dataset.timer = setTimeout(() => { button.textContent = '주소 복사'; button.classList.remove('copied'); }, 2000);
      return;
    }
    let feedback = card.querySelector('.copy-feedback');
    if (!feedback) { feedback = node('p', 'copy-feedback'); feedback.setAttribute('role', 'status'); card.append(feedback); }
    feedback.textContent = COPY.copyFail;
    let manual = card.querySelector('.manual-copy input');
    if (!manual) {
      const label = node('label', 'manual-copy');
      label.append(node('span', 'sr-only', '직접 복사할 지도 검색어'));
      manual = node('input'); manual.readOnly = true; manual.value = search;
      label.append(manual); card.append(label);
    }
    manual.focus(); manual.select();
  }

  function setMapApp(key) {
    if (!MAPS[key]) return;
    state.mapApp = key;
    saveProfile();
    document.querySelectorAll('.facility[data-search]').forEach(card => {
      const query = encodeURIComponent(card.dataset.search);
      const primary = card.querySelector('.go-map');
      if (primary) { primary.href = MAPS[key][1](query); primary.textContent = `${MAPS[key][0]}에서 열기`; }
      const others = card.querySelector('.map-others');
      if (others) others.replaceChildren(...alternatives(card.dataset.search));
      const toggle = card.querySelector('.map-more summary');
      if (toggle) toggle.textContent = '다른 지도로 열기';
    });
  }

  function alternatives(search) {
    const query = encodeURIComponent(search);
    const parts = [];
    MAP_ORDER.filter(key => key !== state.mapApp).forEach(key => {
      const link = node('a', 'map-alt', MAPS[key][0]);
      link.href = MAPS[key][1](query);
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.addEventListener('click', () => { setMapApp(key); announce('지도 앱으로 넘어가요.'); });
      parts.push(link);
    });
    return parts;
  }

  function facilityCard(facility) {
    const card = node('article', 'facility');
    const head = node('div', 'facility-head');
    const mark = node('span', 'picto');
    // 종류별로 스티커 색을 돌려 씁니다. 색은 장식이고 뜻은 아래 시설명이 전합니다.
    mark.dataset.type = text(facility.type) || 'default';
    mark.append(picto(text(facility.type)));
    const title = node('div');
    title.append(node('h4', '', text(facility.name) || FIELD_LABELS[text(facility.type)] || '편의시설'));
    if (text(facility.parent_place)) title.append(node('p', 'facility-parent', text(facility.parent_place)));
    head.append(mark, title);
    card.append(head);

    const dl = node('dl');
    appendPair(dl, '어디 안', facility.location_detail);
    appendPair(dl, '주소', text(facility.address) || COPY.noAddress);
    card.append(dl);

    // 서버가 준 문자열만 그대로 씁니다. 주소를 프런트에서 만들거나 내부 위치를 섞지 않습니다.
    const search = text(facility.map_search_text);
    if (search) {
      card.dataset.search = search;
      const query = encodeURIComponent(search);
      const actions = node('div', 'facility-actions');
      const open = node('a', 'go-map', `${MAPS[state.mapApp][0]}에서 열기`);
      open.href = MAPS[state.mapApp][1](query);
      open.target = '_blank'; open.rel = 'noopener noreferrer';
      open.addEventListener('click', () => announce('지도 앱으로 넘어가요.'));
      const copy = node('button', 'copy-button', '주소 복사');
      copy.type = 'button';
      copy.addEventListener('click', () => copySearch(search, card, copy));
      actions.append(open, copy);
      // 다른 지도 앱은 접어 둡니다. 기본은 마지막에 고른 앱 하나입니다.
      const more = node('details', 'map-more');
      const others = node('div', 'map-others');
      others.append(...alternatives(search));
      more.append(node('summary', '', '다른 지도로 열기'), others);
      card.append(actions, more);
    }
    return card;
  }

  const FACILITY_KEYWORDS = [
    ['수유', 'nursing_room'], ['기저귀', 'diaper_station'], ['화장실', 'restroom'],
    ['휠체어', 'wheelchair_rental'], ['유모차', 'stroller_rental'], ['주차', 'parking'],
    ['엘리베이터', 'elevator'], ['쉬', 'rest_area'], ['휴식', 'rest_area']
  ];

  function cleanDetail(value) {
    return text(value).replace(/_무장애 편의시설/g, '').replace(/\s+/g, ' ').trim();
  }

  function buildUiSummary(data, request) {
    const message = text(request?.message);
    const facilities = list(data.facilities).filter(object);
    const target = FACILITY_KEYWORDS.find(([word]) => message.includes(word));
    if (target) {
      const matched = facilities.find(item => text(item.type) === target[1]);
      if (matched) {
        const name = text(matched.name) || FIELD_LABELS[target[1]] || '시설';
        return `${name} 정보가 확인돼요. 자세한 위치와 이용 정보는 아래 시설 카드에서 볼 수 있어요.`;
      }
    }

    const items = list(data.comfort?.items).filter(object);
    if (items.length) {
      const labels = status => items.filter(item => text(item.status) === status)
        .map(item => FIELD_LABELS[text(item.need)] || text(item.need)).filter(Boolean);
      const satisfied = labels('SATISFIED');
      const conflict = labels('CONFLICT');
      const unknown = labels('UNKNOWN');
      const sentences = [];
      // 사용자가 먼저 알아야 할 위험/미확인 정보를 앞에 두고, 최대 두 문장만 보여줍니다.
      if (conflict.length) sentences.push(`${conflict.slice(0, 2).join('·')}은 현재 조건에서 이용이 불편할 수 있어요.`);
      if (unknown.length) sentences.push(`${unknown.slice(0, 2).join('·')}은 공식 자료에서 아직 확인되지 않았어요.`);
      if (satisfied.length && sentences.length < 2) sentences.push(`${satisfied.slice(0, 2).join('·')}은 공식 정보에서 확인됐어요.`);
      if (sentences.length) return sentences.slice(0, 2).join(' ');
    }

    // success 응답에서는 Backend의 raw answer를 화면에 직접 쓰지 않습니다.
    // 구조화 데이터가 없는 예외 성공 응답도 보고서형 본문 대신 짧은 안내만 표시합니다.
    return '공식 여행 정보를 확인했어요. 아래 항목에서 필요한 내용을 살펴보세요.';
  }

  function checkList(items, className = 'checks') {
    const ul = node('ul', className);
    items.forEach(item => {
      const [icon, word] = STATUS[item.status] || ['?', '상태 미확인'];
      const li = node('li');
      li.dataset.status = STATUS[item.status] ? item.status : 'UNKNOWN';
      li.append(node('span', 'mark', icon));
      const content = node('span', 'check-text');
      const label = text(FIELD_LABELS[text(item.need)] || item.need);
      if (label) content.append(node('b', '', label));
      content.append(node('span', 'reason', STATUS_REASON[item.status] || word));
      li.append(content);
      ul.append(li);
    });
    return ul;
  }

  function renderResponse(data, request) {
    const sheet = node('article', 'sheet');

    // 1층 — 판정 띠와 결론
    if (object(data.comfort)) {
      const level = Object.hasOwn(COMFORT, data.comfort.level) ? data.comfort.level : 'UNRECOGNIZED';
      const [label, keyword] = COMFORT[level] || ['판단 상태를 확인하지 못했어요', ''];
      const verdict = node('p', 'verdict');
      verdict.dataset.level = level;
      const words = node('span');
      words.append(markedText(label, keyword));
      verdict.append(oniFace(level), words);
      sheet.append(verdict);
    }
    const head = node('header', 'sheet-head');
    head.append(node('p', 'sheet-meta', `${FAMILY_LABELS[request.traveler_type]} · ${text(data.place?.region) || '전국 여행 정보'}`));
    if (text(data.place?.name)) head.append(node('h3', '', text(data.place.name)));
    if (text(data.place?.address)) head.append(node('p', 'place-address', text(data.place.address)));
    const uiSummary = buildUiSummary(data, request);
    if (uiSummary) head.append(node('p', 'summary', uiSummary));
    sheet.append(head);

    // 2층 — 내 조건 결과 3줄
    const items = list(data.comfort?.items).filter(item => object(item) && (text(item.reason) || text(item.need)));
    if (items.length) {
      const block = node('section', 'checks-block');
      block.append(ruleLabel('우리 가족 조건'), checkList(items.slice(0, 3)));
      sheet.append(block);
    }

    // 시설 카드 2개 먼저
    const facilities = list(data.facilities).filter(facility => object(facility) && Object.values(facility).some(value => text(value)));
    if (facilities.length) {
      const section = node('section', 'facilities');
      section.append(ruleLabel('가까운 시설'));
      const grid = node('div', 'facility-grid');
      facilities.slice(0, 2).forEach(facility => grid.append(facilityCard(facility)));
      section.append(grid);
      if (facilities.length > 2) {
        const more = node('button', 'more-button', `+ 시설 ${facilities.length - 2}곳 더 보기`);
        more.type = 'button';
        more.addEventListener('click', () => {
          facilities.slice(2).forEach(facility => grid.append(facilityCard(facility)));
          more.remove();
        });
        section.append(more);
      }
      sheet.append(section);
    }

    // 3층 — 접어 두기
    const details = node('details', 'more-details');
    const body = node('div', 'details-body');
    const sections = list(data.sections).filter(section => object(section) && list(section.items).some(item => object(item) && text(item.value)));
    if (sections.length) {
      const grid = node('div', 'detail-grid');
      sections.forEach(section => {
        const block = node('section', 'detail-section');
        block.append(ruleLabel(text(section.title) || SECTION_TITLES[section.key] || '여행 정보'));
        const dl = node('dl');
        list(section.items).filter(object).forEach(item => appendPair(dl, text(item.label) || '안내', item.value));
        block.append(dl); grid.append(block);
      });
      body.append(grid);
    }
    if (items.length > 3) {
      const rest = node('section', 'checks-block');
      rest.append(ruleLabel('남은 조건'), checkList(items.slice(3)));
      body.append(rest);
    }
    const unknown = [...new Set(list(data.unknown_fields).map(text).filter(Boolean))];
    if (unknown.length) {
      const section = node('section', 'unknown note');
      section.append(node('h4', '', '아직 확인 안 된 정보'), node('p', '', COPY.unknown));
      const ul = node('ul');
      unknown.forEach(key => ul.append(node('li', '', FIELD_LABELS[key] || key)));
      section.append(ul); body.append(section);
    }
    const sources = list(data.sources).filter(source => object(source) && (text(source.organization) || text(source.title)));
    if (sources.length) {
      const section = node('section', 'sources');
      section.append(ruleLabel('출처'));
      const ul = node('ul');
      sources.forEach(source => ul.append(node('li', '', [text(source.organization), text(source.title), text(source.updated_at) ? `기준일 ${text(source.updated_at)}` : ''].filter(Boolean).join(' · '))));
      section.append(ul); body.append(section);
    }
    if (body.childElementCount) {
      details.append(node('summary', '', '이동·운영 정보 자세히 보기'), body);
      sheet.append(details);
    }

    // 이어서 물어보기 + 탐색 동작. 추천 질문은 이전 대화를 지우지 않고 새 말풍선으로 이어집니다.
    const placeId = text(data.place?.content_id) || null;
    const followups = state.suggested.slice(0, 3).map(question => questionChip(question, placeId));
    const foot = node('div', 'sheet-foot');
    if (followups.length) {
      foot.append(node('p', 'followup-label', '이어서 물어보기'), chipRow(followups));
    }
    const actions = node('div', 'sheet-actions');
    const other = node('button', 'pick', '다른 곳 보기');
    other.type = 'button';
    other.addEventListener('click', () => {
      closePlace(true);
      state.onboardingTurn?.remove();
      state.onboardingTurn = botTurn(['다음은 어디로 가볼까요?'], placeHints());
      scrollToLatest();
    });
    const conditions = node('button', 'pick', '조건 바꾸기');
    conditions.type = 'button';
    conditions.addEventListener('click', () => { toggleDrawer(true); announce('조건을 바꾸면 다음 질문부터 반영해요.'); });
    actions.append(other, conditions);
    foot.append(actions);
    sheet.append(foot);

    $('chat-window').append(sheet);
  }

  // ── 오류 ──────────────────────────────────────────────────────────
  function regionRetry(request) {
    return ['지역 붙여서 다시 묻기', () => {
      $('user-input').value = request.message;
      $('user-input').focus();
      $('user-input').setSelectionRange(0, 0);
      announce('앞에 시·도 이름을 붙여서 다시 보내주세요.');
    }];
  }

  function candidateChoices(data) {
    return list(data.candidates)
      .filter(candidate => object(candidate) && text(candidate.content_id) && text(candidate.name))
      .slice(0, 5)
      .map(candidate => {
        const name = text(candidate.name);
        const region = text(candidate.region);
        const label = region ? `${name} · ${region}` : name;
        return [label, () => {
          // 후보 선택은 이름을 다시 검색하지 않고 Backend가 준 content_id를 그대로 사용합니다.
          dispatch('선택한 장소 기준으로 현재 조건을 알려줘', text(candidate.content_id), name);
        }];
      });
  }

  function renderError(lines, chips) {
    botTurn(lines, chips, 'alert');
  }

  // ── 전송 ──────────────────────────────────────────────────────────
  function guessFamily(message) {
    const senior = HINTS.senior.some(word => message.includes(word));
    const baby = HINTS.baby.some(word => message.includes(word));
    return senior && baby ? 'both' : senior ? 'senior' : baby ? 'baby' : null;
  }

  function askTraveler(message, placeId) {
    userTurn(displayMessage);
    $('user-input').value = '';
    state.pending = { message, placeId };
    const guess = guessFamily(message);
    const answerWith = type => () => {
      state.confirmTurn = null;
      applyFamily(type);
      const pending = state.pending; state.pending = null;
      if (pending) dispatch(pending.message, pending.placeId);
    };
    const options = Object.keys(FAMILY_LABELS)
      .sort((a, b) => (b === guess) - (a === guess))
      .map(type => [type === guess ? `네, ${FAMILY_SHORT[type]}` : `${FAMILY_SHORT[type]} 가요`, answerWith(type)]);
    botTurn([guess ? `${FAMILY_LABELS[guess]} 가시는 거군요. 맞을까요?` : '누구랑 가세요?'], options);
    scrollToLatest();
  }

  function askInterrupt(message, placeId) {
    state.confirmTurn?.remove();
    const looking = state.placeName ? `지금 ${state.placeName}을 보고 있는데` : '지금 찾고 있는 게 있는데';
    state.confirmTurn = botTurn([`${looking}, 새로 여쭤보신 것부터 볼까요?`], [
      ['새 질문 먼저', () => {
        state.confirmTurn?.remove(); state.confirmTurn = null;
        state.deferred = state.active;
        state.queued = { message, placeId };
        state.interrupting = true;
        state.controller?.abort();
      }],
      ['이거 먼저 볼게요', () => {
        state.confirmTurn?.remove(); state.confirmTurn = null;
        $('user-input').value = message;
        $('user-input').focus();
      }]
    ]);
    $('user-input').value = '';
    scrollToLatest();
  }

  function submitQuestion(raw, placeId = state.currentPlaceId) {
    const message = text(raw);
    if (!message) {
      $('form-feedback').textContent = COPY.empty;
      $('user-input').focus();
      return;
    }
    $('form-feedback').textContent = '';
    if (state.busy) { askInterrupt(message, placeId); return; }
    if (!state.travelerType) { askTraveler(message, placeId); return; }
    dispatch(message, placeId);
  }

  function setBusy(busy) {
    state.busy = busy;
    $('loading').hidden = !busy;
    $('chat-form').setAttribute('aria-busy', String(busy));
    $('send-button').classList.toggle('waiting', busy);
  }

  async function dispatch(message, placeId = state.currentPlaceId, displayMessage = message) {
    const request = { message, traveler_type: state.travelerType, needs: [...state.needs], current_place_id: placeId };
    state.active = request;
    userTurn(message);
    $('user-input').value = '';
    $('user-input').style.height = '';
    $('form-feedback').textContent = '';
    setBusy(true);
    scrollToLatest();

    const controller = new AbortController();
    state.controller = controller;
    $('loading-text').textContent = COPY.loading1;
    const stage2 = setTimeout(() => { $('loading-text').textContent = COPY.loading2; }, 2500);
    const stage3 = setTimeout(() => { $('loading-text').textContent = COPY.loading3; }, 10000);
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      let data;
      if (mockCase) {
        const { getMockResponse } = await import('./mock-data.mjs');
        data = await getMockResponse(mockCase, request, controller.signal);
      } else {
        const response = await fetch(`${apiBase}/chat`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request), signal: controller.signal
        });
        if (!response.ok) throw new Error(`HTTP_${response.status}`);
        try { data = await response.json(); } catch (error) { if (controller.signal.aborted) throw error; throw new Error('INVALID_RESPONSE'); }
      }
      if (!object(data) || typeof data.success !== 'boolean') throw new Error('INVALID_RESPONSE');

      if (data.success === false) {
        const code = text(data.error?.code);
        const notFound = ['PLACE_NOT_FOUND', 'NOT_FOUND'].includes(code);
        const ambiguous = ['AMBIGUOUS_PLACE', 'PLACE_AMBIGUOUS', 'MULTIPLE_PLACES'].includes(code);
        if (notFound || ambiguous) {
          updateContext(null); state.suggested = []; renderQuickActions();
          const candidateChips = ambiguous ? candidateChoices(data) : [];
          renderError(
            [ambiguous ? (text(data.answer) || '검색된 관련 장소가 여러 곳 있어요. 어느 장소인지 골라주세요.') : '그 이름으로는 공식 자료에서 못 찾았어요.',
              ambiguous && candidateChips.length ? '아래 후보를 고르면 같은 가족 조건으로 바로 이어서 확인해요.' : '지역을 같이 알려주시면 다시 찾아볼게요.'],
            candidateChips.length ? candidateChips : [regionRetry(request)]
          );
        } else {
          renderError([text(data.answer) || text(data.error?.message) || '지금은 정보를 가져오기 어려워요.', '잠시 뒤 다시 눌러주세요.'],
            [[COPY.retry, () => dispatch(request.message, request.current_place_id)]]);
        }
      } else {
        const hasContent = text(data.place?.name) || object(data.comfort) || list(data.sections).length || list(data.facilities).length;
        if (!hasContent) throw new Error('INVALID_RESPONSE');
        const nextId = text(data.place?.content_id) || null;
        // 장소가 바뀌면 앞선 장소를 마무리하고 넘어갑니다.
        if (nextId && state.currentPlaceId && nextId !== state.currentPlaceId) closePlace(true);
        state.suggested = [...new Set(list(data.suggested_questions).map(text).filter(Boolean))];
        state.answers += 1;
        state.unknownCount = new Set(list(data.unknown_fields).map(text).filter(Boolean)).size;
        renderResponse(data, request);
        updateContext(data.place);
        state.turns += 1;
        renderQuickActions();
        if (state.deferred) {
          const waiting = state.deferred;
          state.deferred = null;
          botTurn([`아까 여쭤보신 "${waiting.message}"도 이어서 볼까요?`],
            [['네, 이어서', () => dispatch(waiting.message, waiting.current_place_id)]]);
        }
      }
    } catch (error) {
      if (state.interrupting) return;
      if (controller.signal.aborted) {
        renderError(['기다리는 시간이 길어졌어요.', '잠시 뒤 같은 질문을 다시 보내실 수 있어요.'],
          [[COPY.retry, () => dispatch(request.message, request.current_place_id)]]);
      } else if (error.message?.startsWith('HTTP_')) {
        renderError(['잠깐 정보를 못 가져왔어요.', `잠시 뒤 다시 눌러주세요. (HTTP ${error.message.slice(5)})`],
          [[COPY.retry, () => dispatch(request.message, request.current_place_id)]]);
      } else if (error.message === 'INVALID_RESPONSE') {
        renderError(['답변 형식이 맞지 않아 화면에 담지 못했어요.', '서버 연결 상태를 확인한 뒤 다시 보내주세요.'],
          [[COPY.retry, () => dispatch(request.message, request.current_place_id)]]);
      } else {
        renderError(['잠깐 정보를 못 가져왔어요.', '연결 상태를 확인하고 다시 눌러주세요.'],
          [[COPY.retry, () => dispatch(request.message, request.current_place_id)]]);
      }
    } finally {
      clearTimeout(timer); clearTimeout(stage2); clearTimeout(stage3);
      state.controller = null; state.active = null;
      setBusy(false);
      if (state.interrupting) {
        state.interrupting = false;
        const next = state.queued; state.queued = null;
        if (next) { dispatch(next.message, next.placeId); return; }
      }
      scrollToLatest();
    }
  }

  // ── 첫인사 ────────────────────────────────────────────────────────
  function placeHints() {
    const places = ['경복궁', '국립중앙박물관', '국립중앙과학관', '경주 불국사', '성산일출봉', '해운대해수욕장'];
    return places.map(place => [place, () => submitQuestion(place, null)]);
  }

  function showPlacePrompt(type) {
    state.onboardingTurn?.remove();
    state.onboardingTurn = botTurn([`${FAMILY_LABELS[type]}시군요. 어디 가시는지 알려주세요.`], placeHints());
    $('user-input').focus();
    scrollToLatest();
  }

  function askFresh() {
    const ask = $('greeting-ask');
    ask.replaceChildren(node('p', 'ask', '누구랑 가세요?'));
    const types = Object.keys(FAMILY_LABELS);
    const row = chipRow(types.map(type => [FAMILY_SHORT[type], () => {
      applyFamily(type);
      showPlacePrompt(type);
    }]));
    row.querySelectorAll('.pick').forEach((button, index) => { button.dataset.traveler = types[index]; });
    ask.append(row);
  }

  function greet() {
    const saved = loadProfile();
    if (!saved) { askFresh(); return; }
    state.mapApp = MAPS[saved.mapApp] ? saved.mapApp : 'kakao';
    const ask = $('greeting-ask');
    ask.replaceChildren(node('p', 'ask', `지난번처럼 ${FAMILY_LABELS[saved.travelerType]} 가시나요?`));
    ask.append(chipRow([
      ['네, 그대로', () => {
        state.needsTouched = true;
        applyFamily(saved.travelerType, list(saved.needs).filter(key => typeof key === 'string'));
        state.onboardingTurn?.remove();
        state.onboardingTurn = botTurn([`${summaryText()} 조건으로 볼게요.`, '어디 가시는지 알려주세요.'], placeHints());
        $('user-input').focus();
        scrollToLatest();
      }],
      ['아니요, 바꿀게요', () => { askFresh(); $('greeting-ask').querySelector('.pick')?.focus(); }]
    ]));
  }

  // ── 연결 ──────────────────────────────────────────────────────────
  $('condition-toggle').addEventListener('click', () => toggleDrawer());
  $('drawer-close').addEventListener('click', () => {
    toggleDrawer(false);
    $('condition-summary').textContent = summaryText();
    announce(COPY.applied);
    $('condition-toggle').focus();
  });
  $('needs-more').addEventListener('click', () => { state.moreOpen = !state.moreOpen; renderDrawer(); });
  $('chat-form').addEventListener('submit', event => { event.preventDefault(); submitQuestion($('user-input').value); });
  $('user-input').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      submitQuestion($('user-input').value);
    }
  });
  $('user-input').addEventListener('input', event => {
    const field = event.target;
    field.style.height = 'auto';
    field.style.height = `${Math.min(field.scrollHeight, 160)}px`;
  });

  // 모바일 키보드가 올라와도 입력창이 가리지 않게 합니다.
  if (window.visualViewport) {
    const viewport = window.visualViewport;
    const sync = () => {
      const overlap = Math.max(0, window.innerHeight - (viewport.height + viewport.offsetTop));
      document.documentElement.style.setProperty('--keyboard', `${Math.round(overlap)}px`);
    };
    viewport.addEventListener('resize', sync);
    viewport.addEventListener('scroll', sync);
    sync();
  }

  greet();
  renderDrawer();
})();
