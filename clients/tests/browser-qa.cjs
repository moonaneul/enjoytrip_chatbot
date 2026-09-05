/* v5. Run with Node and Playwright. Real Chrome; API fixtures are explicitly mocked. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const url = process.env.FRONTEND_URL || 'http://127.0.0.1:5500';
const out = path.join(__dirname, 'results');
fs.mkdirSync(out, { recursive: true });
const results = [];
let browser;
async function test(name, work) {
  try { await work(); results.push({ name, result: 'PASS' }); console.log('PASS', name); }
  catch (error) { results.push({ name, result: 'FAIL', error: error.message }); console.log('FAIL', name, error.message); }
}
(async () => {
  const { MOCK_RESPONSES } = await import(pathToFileURL(path.join(__dirname, '..', 'mock-data.mjs')).href);
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  // 지도 링크는 새 창으로 열립니다. 메인 페이지를 뺀 팝업만 바로 닫습니다.
  context.on('page', async popup => { if (popup !== page) { try { await popup.close(); } catch { /* 이미 닫힘 */ } } });
  const errors = []; page.on('pageerror', error => errors.push(error.message));

  // 기본은 첫 방문 상태. keep을 붙이면 지난번 기록을 남기고, noStore면 저장 자체를 막습니다.
  await page.addInitScript(() => {
    if (location.search.includes('noStore')) {
      Object.defineProperty(window, 'localStorage', { configurable: true, get() { throw new Error('blocked for QA'); } });
    } else if (!location.search.includes('keep')) {
      try { localStorage.clear(); } catch { /* 접근 불가 환경 */ }
    }
  });

  const open = async (mock = '', flags = '') => {
    const query = [mock ? `mock=${mock}` : '', flags].filter(Boolean).join('&');
    return page.goto(`${url}/index.html${query ? `?${query}` : ''}`);
  };
  // 첫인사 칩으로 유형을 고릅니다. 유형 선택은 관문이 아니라 대화의 한 줄입니다.
  const family = async type => page.locator(`#greeting [data-traveler="${type}"]`).click();
  const openDrawer = async () => { if (await page.locator('#needs-drawer').isHidden()) await page.locator('#condition-toggle').click(); };
  const switchFamily = async type => { await openDrawer(); await page.locator(`#family-options .chip:has(input[value="${type}"])`).click(); };
  const setNeed = async (key, on) => {
    await openDrawer();
    const chip = page.locator(`#needs-options .chip:has(input[value="${key}"])`);
    if (await chip.locator('input').isChecked() !== on) await chip.click();
  };
  const submit = async question => { await page.locator('#user-input').fill(question); await page.locator('#send-button').click(); };
  const done = async () => {
    await page.waitForFunction(() => !document.getElementById('loading').hidden, null, { timeout: 2500 }).catch(() => {});
    await page.waitForFunction(() => document.getElementById('loading').hidden, null, { timeout: 60000 });
  };
  const openDetails = () => page.locator('.more-details').last().evaluate(element => { element.open = true; });
  const expandFacilities = async () => { const more = page.locator('.more-button'); if (await more.count()) await more.first().click(); };
  // fullPage 캡처는 sticky 요소를 멈춘 위치에 그려 화면을 가립니다. 촬영 동안만 흐름에 되돌립니다.
  const shoot = async name => {
    await page.waitForTimeout(350);
    const patch = await page.addStyleTag({ content: '.composer{position:static!important}.skip-link{display:none!important}' });
    await page.screenshot({ path: path.join(out, name), fullPage: true });
    await patch.evaluate(element => element.remove());
  };

  await test('기본 실 API 모드 / 개발자 기능 제거 / 첫 화면에 대화가 먼저', async () => {
    await open();
    assert.equal(await page.locator('#mock-notice').isVisible(), false);
    assert.equal(await page.locator('#greeting [data-traveler]').count(), 3);
    assert.equal(await page.locator('#upload-panel,#rag-toggle,.reset-btn').count(), 0);
    assert(!/SSAFY/.test(await page.locator('body').innerText()));
    assert.equal(await page.locator('#needs-drawer').isVisible(), false);
    assert.equal(await page.locator('#condition-bar').isVisible(), false);
    await shoot('desktop-home.png');
  });

  await test('integrated-v3 빌드 / 전 화면 Gaegu / 내부 Rule 용어 미노출', async () => {
    await open('both');
    assert.equal(await page.locator('html').getAttribute('data-build'), 'integrated-v3');
    const fontChecks = await page.evaluate(() => ({
      body: getComputedStyle(document.body).fontFamily,
      button: getComputedStyle(document.querySelector('button')).fontFamily,
      input: getComputedStyle(document.querySelector('#user-input')).fontFamily
    }));
    assert.match(fontChecks.body, /Gaegu/);
    assert.match(fontChecks.button, /Gaegu/);
    assert.match(fontChecks.input, /Gaegu/);
    await family('both'); await submit('해운대해수욕장'); await done();
    const visible = await page.locator('body').innerText();
    assert.doesNotMatch(visible, /Rule Engine|Comfort 판정|SATISFIED|CONFLICT|UNKNOWN|CHECK_NEEDED|need_nursing_room|need_diaper_station|stroller:/);
    const summary = await page.locator('.sheet').last().locator('.summary').innerText();
    assert(summary.length <= 160);
  });

  await test('빈 질문만 차단 / 유형 미선택은 차단하지 않고 되묻기', async () => {
    await submit('   ');
    assert.match(await page.locator('#form-feedback').innerText(), /어디를 가시는지 알려주세요/);
    assert.equal(await page.locator('.turn.user').count(), 0);
    await submit('엄마랑 경복궁 가려는데 계단 많아?');
    assert.equal(await page.locator('.turn.user').count(), 1);
    assert.match(await page.locator('.turn.bot').last().innerText(), /부모님과 함께 가시는 거군요/);
    assert.equal(await page.locator('#loading').isVisible(), false);
  });

  await test('되묻기 칩이 직전 질문을 그대로 다시 보냄', async () => {
    await page.route('**/chat', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESPONSES.senior) }));
    const request = page.waitForRequest('**/chat');
    await page.locator('.turn.bot').last().locator('.pick').first().click();
    const sent = (await request).postDataJSON();
    await done();
    assert.equal(sent.message, '엄마랑 경복궁 가려는데 계단 많아?');
    assert.equal(sent.traveler_type, 'senior');
    assert.deepEqual(sent.needs, ['stairs_difficult', 'need_rest_area', 'restroom_important']);
    assert.equal(await page.locator('.sheet').count(), 1);
    await page.unroute('**/chat');
  });

  await test('조건 서랍: senior 5개, both는 6개+더보기, 요약 갱신', async () => {
    await open(); await family('senior');
    assert.match(await page.locator('#condition-summary').innerText(), /부모님과 함께 · 계단, 휴식, 화장실/);
    await openDrawer();
    assert.equal(await page.locator('#needs-options .chip').count(), 5);
    await setNeed('need_rest_area', false);
    assert.match(await page.locator('#condition-summary').innerText(), /계단, 화장실/);
    await switchFamily('both');
    assert.equal(await page.locator('#needs-options .chip').count(), 6);
    await page.locator('#needs-more').click();
    assert.equal(await page.locator('#needs-options .chip').count(), 10);
    assert.equal(await page.locator('#needs-options input[value="stairs_difficult"]').isChecked(), true);
    await switchFamily('baby');
    assert.equal(await page.locator('#needs-options input[value="stairs_difficult"]').count(), 0);
    await page.locator('#drawer-close').click();
    assert.equal(await page.locator('#needs-drawer').isVisible(), false);
  });

  await test('초기 장소 추천 6개 / 클릭 시 바로 조회 / 입력 조합 안전', async () => {
    await open(); await family('senior');
    const prompt = page.locator('.turn.bot').last();
    assert.equal(await prompt.locator('.pick').count(), 6);
    assert.deepEqual((await prompt.locator('.pick').allTextContents()).slice(0, 2), ['경복궁', '국립중앙박물관']);
    await page.route('**/chat', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESPONSES.senior) }));
    const request = page.waitForRequest('**/chat');
    await prompt.locator('.pick').first().click();
    const sent = (await request).postDataJSON();
    await done();
    assert.equal(sent.message, '경복궁');
    assert.equal(await page.locator('.turn.user').last().innerText(), '경복궁');
    assert.equal(await page.locator('#quick-actions .pick').count(), 0);
    await page.unroute('**/chat');
    await page.locator('#user-input').fill('테스트');
    await page.locator('#user-input').press('Shift+Enter');
    await page.locator('#user-input').dispatchEvent('keydown', { key: 'Enter', isComposing: true });
  });

  for (const [scenario, type, level, count] of [['senior', 'senior', 'CHECK_NEEDED', 1], ['baby', 'baby', 'COMFORTABLE', 3], ['both', 'both', 'CHECK_NEEDED', 2], ['burden', 'senior', 'BURDEN_POSSIBLE', 0], ['insufficient', 'both', 'INSUFFICIENT_DATA', 0]]) {
    await test(`Mock ${scenario}: ${level}, 시설 ${count}개`, async () => {
      await open(scenario); await family(type); await submit('가족과 여행하기 괜찮을까?'); await done();
      assert.equal(await page.locator(`.verdict[data-level="${level}"]`).count(), 1);
      // 2층은 최대 3줄, 나머지는 3층으로 내려갑니다.
      const front = page.locator('.sheet > .checks-block .checks li');
      assert(await front.count() > 0);
      assert(await front.count() <= 3);
      assert.equal(await page.locator('.facility').count(), Math.min(count, 2));
      await expandFacilities();
      assert.equal(await page.locator('.facility').count(), count);
      if (!count) assert.equal(await page.locator('.facilities').count(), 0);
      await openDetails().catch(() => {});
      if (count) assert.match(await page.locator('.sources').innerText(), /화면 테스트용 기관/);
      if (scenario === 'both') { assert.equal(await page.locator('.unknown li').count(), 4); await shoot('desktop-both.png'); }
      if (scenario === 'insufficient') assert.equal(await page.locator('.detail-section').count(), 0);
    });
  }

  await test('3층은 기본으로 접혀 있음', async () => {
    await open('senior'); await family('senior'); await submit('경복궁'); await done();
    assert.equal(await page.locator('.more-details').first().evaluate(element => element.open), false);
    assert.equal(await page.locator('.unknown').isVisible(), false);
    assert.match(await page.locator('.more-details summary').first().innerText(), /이동·운영 정보 자세히 보기/);
    await page.locator('.more-details summary').first().click();
    assert.equal(await page.locator('.unknown').isVisible(), true);
  });

  await test('지도 링크: 인코딩·rel·target·앱 3종', async () => {
    await open('baby'); await family('baby'); await submit('수유실 확인해줘'); await done();
    const facility = MOCK_RESPONSES.baby.facilities[0];
    const expected = encodeURIComponent(facility.map_search_text);
    const primary = page.locator('.facility').first().locator('.go-map');
    assert.equal(await primary.getAttribute('href'), `https://map.kakao.com/link/search/${expected}`);
    assert.equal(await primary.getAttribute('target'), '_blank');
    assert.equal(await primary.getAttribute('rel'), 'noopener noreferrer');
    assert.match(await primary.innerText(), /카카오맵에서 열기/);
    // 내부 위치는 검색어에 섞이지 않습니다.
    assert.equal(decodeURIComponent(expected).includes(facility.location_detail), false);
    await page.locator('.facility').first().locator('.map-more summary').click();
    const alts = page.locator('.facility').first().locator('.map-alt');
    assert.equal(await alts.count(), 2);
    assert.deepEqual(await alts.allTextContents(), ['네이버지도', '구글지도']);
    assert.equal(await alts.nth(0).getAttribute('href'), `https://map.naver.com/p/search/${expected}`);
    assert.equal(await alts.nth(1).getAttribute('href'), `https://www.google.com/maps/search/?api=1&query=${expected}`);
  });

  await test('지도 앱 선택을 기억하고 다음 카드에 반영', async () => {
    await page.locator('.facility').first().locator('.map-alt').first().click();
    await page.waitForFunction(() => /네이버지도에서 열기/.test(document.querySelector('.go-map').textContent));
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('onga.profile.v1') || '{}'));
    assert.equal(saved.mapApp, 'naver');
    await submit('기저귀 갈 곳은?'); await done();
    assert.match(await page.locator('.sheet').last().locator('.go-map').first().innerText(), /네이버지도에서 열기/);
  });

  await test('시설 종류 픽토그램 / 아이콘 옆 시설명 텍스트', async () => {
    await open('many'); await family('both'); await submit('경복궁'); await done();
    await expandFacilities();
    const cards = page.locator('.facility');
    assert.equal(await cards.count(), 4);
    for (let index = 0; index < 4; index += 1) {
      assert.equal(await cards.nth(index).locator('.picto svg').count(), 1);
      assert(await cards.nth(index).locator('h4').innerText());
    }
    // 미등록 type도 기본 핀으로 그려집니다.
    assert.equal(await page.evaluate(() => document.querySelectorAll('.picto svg > *').length > 0), true);
  });

  await test('시설 위치·주소·Clipboard API 실제 복사와 버튼 내 피드백', async () => {
    await open('baby'); await family('baby'); await submit('수유실 확인해줘'); await done();
    assert.match(await page.locator('.facility').first().innerText(), /어린이박물관 1층/);
    await page.locator('.copy-button').first().click();
    await page.locator('.copy-button').first().filter({ hasText: '복사했어요' }).waitFor();
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), MOCK_RESPONSES.baby.facilities[0].map_search_text);
    assert.equal(await page.locator('#toast').count(), 0);
  });

  await test('Clipboard 실패 → 실제 execCommand fallback', async () => {
    await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new Error('Denied for QA'); }; });
    await page.locator('.copy-button').nth(1).click();
    assert.match(await page.locator('.facility').nth(1).innerText(), /복사했어요/);
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), MOCK_RESPONSES.baby.facilities[1].map_search_text);
  });

  await test('두 복사 방식 실패 → 수동 선택 fallback', async () => {
    await page.evaluate(() => { document.execCommand = () => false; });
    await page.locator('.copy-button').first().click();
    assert.equal(await page.locator('.manual-copy input').inputValue(), MOCK_RESPONSES.baby.facilities[0].map_search_text);
    assert.match(await page.locator('.facility').first().innerText(), /직접 복사/);
  });

  await test('주소 없음 / 검색어 null·공백이면 지도 링크와 복사 버튼 모두 생략', async () => {
    await open('no_address'); await family('senior'); await submit('화장실'); await done();
    assert.match(await page.locator('.facility').innerText(), /확인된 자료가 없어요/);
    await open('no_map'); await family('senior'); await submit('화장실'); await done();
    assert.equal(await page.locator('.copy-button').count(), 0);
    assert.equal(await page.locator('.go-map').count(), 0);
    assert.equal(await page.locator('.map-more').count(), 0);
    assert.equal(await page.locator('.facility').count(), 2);
  });

  const personas = {
    senior: ['엄마가 계단을 잘 못 오르는데 경복궁 괜찮아?', '아빠가 오래 못 걷는데 많이 걸어야 해?', '중간에 쉴 곳 있어?', '휠체어 빌릴 수 있어?', '화장실 이용하기 편해?'],
    baby: ['유모차로 다닐 수 있어?', '수유실 있어?', '기저귀 갈 곳 있어?', '엘리베이터 있어?', '주차 후 유모차로 이동하기 편해?'],
    both: ['부모님하고 두 살 아이 모두 같이 가도 괜찮을까?', '쉬는 곳이랑 수유실 둘 다 확인해줘.']
  };
  for (const [type, questions] of Object.entries(personas)) {
    await test(`Persona ${type}: ${questions.length}개 실제 질문 입력·응답 렌더링 (가상 응답)`, async () => {
      await open(type); await family(type);
      for (const question of questions) { await submit(question); await done(); }
      assert.equal(await page.locator('.sheet').count(), questions.length);
      assert.deepEqual(await page.locator('.turn.user').allTextContents(), questions);
    });
  }

  for (const [scenario, expected] of [['not_found', '공식 자료에서 못 찾았어요'], ['failure', '가져오기 어려워요'], ['network', '잠깐 정보를 못 가져왔어요'], ['http_error', 'HTTP 503']]) {
    await test(`오류 ${scenario}: 이유와 다음 행동을 함께 안내`, async () => {
      await open(scenario); await family('both'); await submit('여행지'); await done();
      const card = page.locator('.turn.alert');
      assert.match(await card.innerText(), new RegExp(expected));
      assert.equal(await card.locator('.pick').count(), 1);
      assert.equal(await page.locator('.sheet').count(), 0);
    });
  }

  await test('AMBIGUOUS_PLACE: Backend 후보를 직접 선택', async () => {
    await open('ambiguous'); await family('both'); await submit('해운대'); await done();
    const card = page.locator('.turn.alert').last();
    assert.match(await card.innerText(), /검색된 관련 장소가 여러 곳/);
    assert.equal(await card.locator('.pick').count(), MOCK_RESPONSES.ambiguous.candidates.length);
    assert.match(await card.locator('.pick').first().innerText(), /해운대해수욕장/);
  });

  const requests = [];
  let responseBody = structuredClone(MOCK_RESPONSES.senior);
  let httpStatus = 200;
  let routeDelay = 0;
  await page.route('**/chat', async route => {
    requests.push(route.request().postDataJSON());
    if (routeDelay) await new Promise(resolve => setTimeout(resolve, routeDelay));
    await route.fulfill({ status: httpStatus, contentType: 'application/json', body: JSON.stringify(responseBody) });
  });

  await test('fetch 경로 Shared Request 정확성·Enter 전송·Loading', async () => {
    await open(); await family('senior');
    await setNeed('need_rest_area', false); await setNeed('restroom_important', false);
    await page.locator('#drawer-close').click();
    routeDelay = 600;
    await page.locator('#user-input').fill('엄마랑 경복궁');
    await page.locator('#user-input').press('Enter');
    assert.equal(await page.locator('#loading').isVisible(), true);
    await done(); routeDelay = 0;
    assert.equal(requests.length, 1);
    assert.deepEqual(requests[0], { message: '엄마랑 경복궁', traveler_type: 'senior', needs: ['stairs_difficult'], current_place_id: null });
    assert.equal(await page.locator('.sheet').count(), 1);
  });

  await test('Backend 추천 우선·follow-up ID·새 장소 전환·명시적 마무리', async () => {
    const followups = page.locator('.sheet').last().locator('.sheet-foot .chip-row .pick');
    assert.deepEqual(await followups.allTextContents(), responseBody.suggested_questions);
    await followups.first().click(); await done();
    assert.equal(requests.at(-1).current_place_id, 'mock-palace');
    responseBody = structuredClone(MOCK_RESPONSES.baby);
    await submit('국립중앙박물관은 어때?'); await done();
    assert.equal(requests.at(-1).current_place_id, 'mock-palace');
    assert.match(await page.locator('.divider').last().innerText(), /여기까지예요/);
    await submit('수유실은?'); await done();
    assert.equal(requests.at(-1).current_place_id, 'mock-museum');
    await page.locator('.context-line .link-button').click();
    await submit('다른 관광지'); await done();
    assert.equal(requests.at(-1).current_place_id, null);
  });

  await test('끼어들기: 새 질문 확인 → 기존 질문 상기', async () => {
    await open(); await family('senior');
    routeDelay = 1500;
    await submit('경복궁 계단 많아?');
    await page.waitForFunction(() => !document.getElementById('loading').hidden);
    const before = requests.length;
    await submit('국립중앙박물관은?');
    assert.match(await page.locator('.turn.bot').last().innerText(), /새로 여쭤보신 것부터 볼까요/);
    assert.equal(requests.length, before);
    await page.locator('.turn.bot').last().locator('.pick').first().click();
    routeDelay = 0; await done();
    assert.equal(requests.at(-1).message, '국립중앙박물관은?');
    assert.match(await page.locator('.turn.bot').last().innerText(), /아까 여쭤보신 "경복궁 계단 많아\?"도 이어서/);
    assert.equal(await page.locator('.turn.alert').count(), 0);
    await page.locator('.turn.bot').last().locator('.pick').click(); await done();
    assert.equal(requests.at(-1).message, '경복궁 계단 많아?');
  });

  await test('모호한 장소 오류 후 후보 content_id로 확정', async () => {
    responseBody = structuredClone(MOCK_RESPONSES.ambiguous); await submit('해운대'); await done();
    assert.equal(await page.locator('.context-line').count(), 0);
    responseBody = structuredClone(MOCK_RESPONSES.baby);
    await page.locator('.turn.alert').last().locator('.pick').first().click(); await done();
    assert.equal(requests.at(-1).current_place_id, 'mock-haeundae-beach');
    assert.equal(requests.at(-1).message, '선택한 장소 기준으로 현재 조건을 알려줘');
  });

  await test('응답 문자열 HTML 실행 방지·알 수 없는 enum·빈 섹션 제외', async () => {
    responseBody = { success: true, answer: '<img src=x onerror="window.xss=1"> 안전합니다', comfort: { level: 'NEW_UNKNOWN', label: '안전합니다', items: [null] }, sections: [{ title: '빈 섹션', items: [] }], facilities: [null, {}], sources: [], unknown_fields: [] };
    await submit('<script>alert(1)</script>'); await done();
    assert.equal(await page.locator('.sheet').last().locator('img,script').count(), 0);
    assert.equal(await page.locator('.verdict').last().getAttribute('data-level'), 'UNRECOGNIZED');
    assert.equal(await page.locator('.sheet').last().locator('.detail-section,.facilities,.sources').count(), 0);
  });

  await test('기존 API 응답·깨진 구조는 형식 오류 / 실제 HTTP 오류 처리', async () => {
    responseBody = { answer: '기존 일반 답변', source: '일반 지식' }; await submit('경복궁'); await done();
    assert.match(await page.locator('.turn.alert').last().innerText(), /답변 형식/);
    httpStatus = 503; await submit('경복궁'); await done();
    assert.match(await page.locator('.turn.alert').last().innerText(), /HTTP 503/); httpStatus = 200;
  });

  await test('로딩 3단계와 45초 timeout 해제 (브라우저 시계 진행)', async () => {
    await page.unroute('**/chat'); await open('timeout'); await family('both');
    await page.clock.install();
    const moduleLoaded = page.waitForResponse(response => response.url().includes('mock-data.mjs'));
    await submit('경복궁'); await moduleLoaded;
    assert.match(await page.locator('#loading-text').innerText(), /찾고 있어요/);
    await page.clock.runFor(3000); assert.match(await page.locator('#loading-text').innerText(), /맞춰보고 있어요/);
    await page.clock.runFor(8000); assert.match(await page.locator('#loading-text').innerText(), /오래 걸리네요/);
    await page.clock.runFor(35000); await done();
    assert.match(await page.locator('.turn.alert').innerText(), /기다리는 시간이 길어졌어요/);
    await page.clock.resume();
  });

  await test('재방문: 지난번 조건을 기억하고 복원', async () => {
    await open('senior'); await family('senior');
    await setNeed('need_rest_area', false); await page.locator('#drawer-close').click();
    await open('senior', 'keep');
    assert.match(await page.locator('#greeting-ask').innerText(), /지난번처럼 부모님과 함께 가시나요/);
    await page.locator('#greeting-ask .pick').first().click();
    assert.match(await page.locator('#condition-summary').innerText(), /부모님과 함께 · 계단, 화장실/);
    assert.equal(await page.locator('#condition-summary').innerText().then(value => value.includes('휴식')), false);
    await submit('경복궁'); await done();
    assert.deepEqual((await page.evaluate(() => window.__lastRequest)) ?? null, null);
    assert.equal(await page.locator('.sheet').count(), 1);
  });

  await test('재방문 거절 / 30일 지난 기록은 무시', async () => {
    await open('senior', 'keep');
    await page.locator('#greeting-ask .pick').nth(1).click();
    assert.match(await page.locator('#greeting-ask').innerText(), /누구랑 가세요/);
    assert.equal(await page.locator('#greeting [data-traveler]').count(), 3);
    await page.evaluate(() => localStorage.setItem('onga.profile.v1', JSON.stringify({ travelerType: 'senior', needs: [], mapApp: 'kakao', savedAt: '2020-01-01T00:00:00.000Z' })));
    await open('senior', 'keep');
    assert.match(await page.locator('#greeting-ask').innerText(), /누구랑 가세요/);
  });

  await test('구버전 localStorage 조건 마이그레이션', async () => {
    await page.evaluate(() => localStorage.setItem('onga.profile.v1', JSON.stringify({ travelerType: 'senior', needs: ['long_walk_difficult', 'driving', 'stairs_difficult'], mapApp: 'kakao', savedAt: new Date().toISOString() })));
    await open('senior', 'keep');
    await page.locator('#greeting-ask .pick').first().click();
    assert.match(await page.locator('#condition-summary').innerText(), /걷기/);
    assert.equal((await page.locator('#condition-summary').innerText()).includes('차'), false);
  });

  await test('localStorage가 막혀도 첫 방문처럼 동작', async () => {
    await open('senior', 'noStore');
    assert.match(await page.locator('#greeting-ask').innerText(), /누구랑 가세요/);
    await family('senior'); await submit('경복궁'); await done();
    assert.equal(await page.locator('.sheet').count(), 1);
    assert.equal(errors.length, 0, errors.join(' / '));
  });

  await test('320·360·390·430·768px 가로 넘침 없음 / 중첩 스크롤 없음', async () => {
    for (const width of [320, 360, 390, 430, 768]) {
      await page.setViewportSize({ width, height: 844 });
      await open('both'); await family('both'); await submit('부모님과 아이 모두'); await done();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}`);
      assert.equal(await page.evaluate(() => {
        const thread = document.getElementById('chat-window');
        return getComputedStyle(thread).overflowY === 'visible' && thread.scrollHeight <= thread.clientHeight + 2;
      }), true, `nested scroll at ${width}`);
      if (width === 390) await shoot('mobile-both.png');
    }
    await page.setViewportSize({ width: 1440, height: 1050 });
  });

  await test('접근성: 본문 15px 이상, 터치 48px 이상, 입력 16px 이상', async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await open('baby'); await family('baby'); await submit('수유실'); await done();
    await openDetails();
    await page.locator('.map-more summary').first().click();
    const audit = await page.evaluate(() => {
      const visible = [...document.querySelectorAll('body *')].filter(element => element.offsetParent !== null);
      const small = visible
        .filter(element => [...element.childNodes].some(node => node.nodeType === 3 && node.textContent.trim()))
        .filter(element => parseFloat(getComputedStyle(element).fontSize) < 15)
        .map(element => element.className + ':' + getComputedStyle(element).fontSize);
      const tiny = [...document.querySelectorAll('button, .chip, .pick, .map-alt, .go-map, a.brand')]
        .filter(element => { const box = element.getBoundingClientRect(); return box.height > 0 && box.height < 48; })
        .map(element => element.className + ' ' + element.textContent.trim().slice(0, 12) + ':' + Math.round(element.getBoundingClientRect().height));
      return { small, tiny, input: getComputedStyle(document.getElementById('user-input')).fontSize };
    });
    assert.deepEqual(audit.small, []);
    assert.deepEqual(audit.tiny, []);
    assert.equal(parseFloat(audit.input) >= 16, true);
    assert.match(await page.locator('body').evaluate(element => getComputedStyle(element).fontFamily), /Gaegu/);
    await page.setViewportSize({ width: 1440, height: 1050 });
  });

  await test('대비: 본문·버튼·placeholder 4.5:1 이상', async () => {
    await open('both'); await family('both'); await submit('경복궁'); await done();
    await openDetails();
    const report = await page.evaluate(() => {
      const parse = value => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
      const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
      const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + .05) / (y + .05); };
      const backdrop = element => {
        for (let cursor = element; cursor; cursor = cursor.parentElement) {
          const color = getComputedStyle(cursor).backgroundColor;
          if (color && !/rgba\(0, 0, 0, 0\)|transparent/.test(color)) return parse(color);
        }
        return [255, 255, 255];
      };
      const rows = [];
      [...document.querySelectorAll('body *')]
        .filter(element => element.offsetParent !== null)
        .filter(element => [...element.childNodes].some(node => node.nodeType === 3 && node.textContent.trim()))
        .forEach(element => {
          const style = getComputedStyle(element);
          const size = parseFloat(style.fontSize);
          const bold = Number(style.fontWeight) >= 700;
          const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
          rows.push({ what: element.className || element.tagName, value: Math.round(ratio(parse(style.color), backdrop(element)) * 100) / 100, need });
        });
      const field = document.getElementById('user-input');
      const holder = getComputedStyle(field, '::placeholder').color;
      rows.push({ what: 'placeholder', value: Math.round(ratio(parse(holder), backdrop(field)) * 100) / 100, need: 4.5 });
      return rows.sort((a, b) => a.value - b.value);
    });
    fs.writeFileSync(path.join(out, 'contrast.json'), JSON.stringify(report.slice(0, 12), null, 2));
    const failed = report.filter(row => row.value < row.need);
    assert.deepEqual(failed, [], JSON.stringify(failed.slice(0, 6)));
  });

  await test('손글씨는 액센트에만 — 금지 구역 0건', async () => {
    await open('baby'); await family('baby'); await submit('수유실 확인해줘'); await done();
    await openDetails();
    const report = await page.evaluate(() => {
      const hand = /gaegu|nanum pen/i;
      const first = element => getComputedStyle(element).fontFamily.split(',')[0].replace(/["']/g, '').trim();
      const banned = '.place-address,.facility h4,.verdict,.reason,.check-text,.turn.alert p,.go-map,.copy-button,.map-alt,#user-input,.sources li,.sheet-head h3,.facility dd,.facility dt';
      const accents = '.brand-name,h1,.kicker,.rule-label,.turn-body .lead,.unknown h4';
      return {
        leaks: [...document.querySelectorAll(banned)].filter(el => hand.test(first(el))).map(el => el.className || el.tagName),
        accents: [...document.querySelectorAll(accents)].map(el => ({
          what: el.className || el.tagName, font: first(el), size: parseFloat(getComputedStyle(el).fontSize)
        }))
      };
    });
    assert.deepEqual(report.leaks, []);
    // 손글씨가 실제로 걸린 자리는 19px 이상이어야 합니다.
    const small = report.accents.filter(row => /gaegu|nanum pen/i.test(row.font) && row.size < 19);
    assert.deepEqual(small, [], JSON.stringify(small));
  });

  await test('온이 표정 4종이 판정과 1:1로 바뀌고 문구가 함께 있다', async () => {
    const seen = new Set();
    for (const [scenario, type, level] of [['senior', 'senior', 'CHECK_NEEDED'], ['baby', 'baby', 'COMFORTABLE'], ['burden', 'senior', 'BURDEN_POSSIBLE'], ['insufficient', 'both', 'INSUFFICIENT_DATA']]) {
      await open(scenario); await family(type); await submit('경복궁'); await done();
      const verdict = page.locator(`.verdict[data-level="${level}"]`);
      assert.equal(await verdict.count(), 1);
      assert.equal(await verdict.locator('svg.oni').count(), 1);
      assert(await verdict.innerText());
      seen.add(await verdict.locator('svg.oni').evaluate(element => element.innerHTML));
    }
    assert.equal(seen.size, 4, '표정 4종이 서로 달라야 합니다');
  });

  await test('장식은 전부 aria-hidden이고 클릭을 가로채지 않는다', async () => {
    await open(); 
    const bad = await page.evaluate(() => [...document.querySelectorAll('.doodle,.oni')]
      .filter(el => el.getAttribute('aria-hidden') !== 'true' || getComputedStyle(el).pointerEvents === 'auto' && el.classList.contains('doodle'))
      .map(el => el.getAttribute('class')));
    assert.deepEqual(bad, []);
  });

  await test('회전이 걸린 요소는 전부 1도 이하', async () => {
    await open('many'); await family('both'); await submit('경복궁'); await done();
    await expandFacilities(); await openDetails();
    const angles = await page.evaluate(() => [...document.querySelectorAll('body *')]
      .filter(el => el.offsetParent !== null)
      .map(el => {
        const matrix = new DOMMatrixReadOnly(getComputedStyle(el).transform);
        return Math.abs(Math.atan2(matrix.b, matrix.a) * 180 / Math.PI);
      })
      .filter(angle => angle > 0.01));
    assert.equal(angles.every(angle => angle <= 1.01), true, JSON.stringify(angles.slice(0, 5)));
  });

  await test('웹폰트를 차단해도 화면이 깨지지 않는다', async () => {
    await page.route('**/*', route => /fonts\.googleapis|fonts\.gstatic|cdn\.jsdelivr/.test(route.request().url()) ? route.abort() : route.continue());
    await open('senior'); await family('senior'); await submit('경복궁'); await done();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.equal(await page.locator('.sheet').count(), 1);
    assert.equal(await page.locator('#send-button').isVisible(), true);
    await shoot('nofont-home.png');
    await page.unroute('**/*');
  });

  await test('prefers-contrast: more에서 테두리가 굵어지고 장식이 사라짐', async () => {
    await open('senior'); await family('senior'); await submit('경복궁'); await done();
    const base = await page.locator('.sheet').evaluate(element => getComputedStyle(element).borderTopWidth);
    await page.emulateMedia({ contrast: 'more' });
    await open('senior'); await family('senior'); await submit('경복궁'); await done();
    const strong = await page.locator('.sheet').evaluate(element => getComputedStyle(element).borderTopWidth);
    assert.equal(base, '2px');
    assert.equal(strong, '3px');
    assert.equal(await page.locator('.doodle').first().isVisible(), false);
    await page.emulateMedia({ contrast: null });
  });

  await test('prefers-reduced-motion에서 애니메이션 정지', async () => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await open('senior'); await family('senior'); await submit('경복궁'); await done();
    const names = await page.evaluate(() => [...document.querySelectorAll('.sheet,.turn,.loading .bar')].map(element => getComputedStyle(element).animationName));
    assert.deepEqual([...new Set(names)], ['none']);
    await page.emulateMedia({ reducedMotion: null });
  });

  await test('실제 Backend 접속 시도 (Mock·route interception 없음)', async () => {
    await open(); await family('senior');
    let networkResult = null;
    const onFailure = request => { if (request.url().endsWith('/chat')) networkResult = request.failure()?.errorText; };
    page.on('requestfailed', onFailure);
    let apiResult = null;
    const capture = async response => {
      if (!response.url().endsWith('/chat') || response.request().method() !== 'POST') return;
      let data; try { data = await response.json(); } catch { data = null; }
      apiResult = { status: response.status(), responseKeys: data ? Object.keys(data) : [], request: response.request().postDataJSON() };
    };
    page.on('response', capture);
    await submit('엄마가 계단을 잘 못 오르는데 경복궁 괜찮아?'); await done();
    const rendered = await page.locator('.sheet').count();
    const info = rendered ? await page.locator('.sheet').innerText() : await page.locator('.turn.alert').innerText();
    fs.writeFileSync(path.join(out, 'backend-integration.json'), JSON.stringify({ testedAt: new Date().toISOString(), url: 'http://127.0.0.1:8000/chat', structuredResponseRendered: !!rendered, networkResult, apiResult, screen: info }, null, 2));
    page.off('response', capture);
    page.off('requestfailed', onFailure);
    console.log('BACKEND', networkResult || info.slice(0, 100));
    // Passing this probe means the result was recorded, NOT that backend integration succeeded.
  });

  await test('브라우저 JavaScript 미처리 오류 없음', async () => assert.deepEqual(errors, []));
  fs.writeFileSync(path.join(out, 'browser-qa.json'), JSON.stringify({ testedAt: new Date().toISOString(), browser: await browser.version(), results }, null, 2));
  await browser.close();
  process.exitCode = results.some(result => result.result === 'FAIL') ? 1 : 0;
})().catch(async error => { console.error(error); if (browser) await browser.close(); process.exitCode = 1; });
