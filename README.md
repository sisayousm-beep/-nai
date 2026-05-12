# NAI Character Batch Runner

NovelAI API 기반 **캐릭터 × 프롬프트 자동 순회 배치 생성** 데스크톱-스타일 웹앱.
설계 문서(`NAI_Character_Batch_Runner_설계도_보고서.pdf`)의 MVP 범위를 단일 HTML 파일로 구현했다.

## 특징

- 캐릭터 N명 × 프롬프트 M개 조합을 큐로 만들어 순차 실행
- 일시정지 / 재개 / 중단 / 실패 재시도
- 캐릭터별 폴더에 PNG + `metadata.json` 자동 저장
- 세션 단위 결과 관리 및 기록
- 토큰 마스킹, 로그/메타데이터에 토큰 미노출

## 실행

추가 빌드 없이 `index.html`을 브라우저에서 열면 된다. **Chrome 또는 Edge 최신 버전 권장** (File System Access API 필요).

로컬 정적 서버로 띄우려면:

```sh
python -m http.server 5173
# 브라우저에서 http://localhost:5173/index.html 열기
```

## 사용 순서

1. **설정** 페이지에서 NovelAI API 토큰 입력 + 검증, 출력 폴더 선택
2. **캐릭터** 페이지에서 캐릭터 등록 (basePrompt, negativePrompt, seed 정책)
3. **프롬프트 세트** 페이지에서 슬롯 직접 추가하거나, **NAIS preset JSON 가져오기**로 일괄 등록
4. **배치 실행** 페이지에서 캐릭터들 + 세트 선택 → 프리셋 설정 → `큐 생성` → `실행`
5. 결과는 `출력폴더/{날짜_세션명}/{캐릭터명}/{슬롯제목_seed}.png` 형식으로 저장

## 배치 공통 Prompt / Undesired Content

배치 실행 페이지의 **배치 공통 Prompt / Undesired Content** 카드는 NovelAI 본가 UI의 "Prompt" + "Undesired Content" 입력란과 같은 동작을 한다.

- **Prompt** (배치 공통): 작가 태그, 퀄리티/스타일 태그처럼 모든 작업에 공통으로 들어갈 문구. 캐릭터 basePrompt 와 슬롯 프롬프트 앞에 위치한다.
- **Quality Tags Enabled** 토글: 켜면 모델별 NAI 기본 퀄리티 프리셋(`rating:general, best quality, very aesthetic, absurdres` 등)을 자동으로 맨 앞에 붙인다.
- **Undesired Content** (배치 공통): 공통 네거티브 문구.
- **UC Preset** 드롭다운: `없음 / Light / Heavy / Human Focus` 중 선택. NAI 본가의 UC Preset과 동일한 의미. 선택하면 해당 프리셋이 네거티브 맨 앞에 추가된다.
- **최종 프롬프트 미리보기** 버튼으로 어떤 순서로 합성되는지 시각적으로 확인 가능.

합성 순서:

```
Prompt   = [Quality preset?] + [Batch Prompt] + [Character.basePrompt] + [Slot.prompt]
Negative = [UC preset?]      + [Batch Undesired] + [Slot.neg OR Character.neg]
```

배치 설정은 `localStorage`에 자동 저장되고, 세션 객체에도 함께 박제되어 실패 재시도 시 동일하게 적용된다.

## NAIS preset 가져오기 / 내보내기

- **가져오기**: 프롬프트 세트 페이지 우상단 `JSON 가져오기 (NAIS)` 버튼으로 NAIS Image Studio의 preset JSON을 그대로 업로드. 각 scene의 `name`이 슬롯 제목(=파일명)으로, `scenePrompt`가 프롬프트로 들어가며, scene별 `width`/`height` 오버라이드도 그대로 보존된다.
- **내보내기 (개별)**: 각 세트 카드의 `내보내기` 버튼 → NAIS 호환 JSON 파일 다운로드.
- **내보내기 (전체)**: 우상단 `전체 백업 내보내기` 버튼 → 모든 프롬프트 세트를 한 파일에 묶은 백업 JSON 다운로드.
- **가중치 변환**: NAIS의 `N::content::` / `-N::content::` 문법은 실행 시점에 NovelAI의 `{...}` × N / `[...]` × N 강조/감쇠로 자동 변환된다 (저장된 슬롯 텍스트는 원본 그대로 유지).

## 기술 스택

- React 18 + TailwindCSS (CDN)
- Babel standalone (런타임 JSX 트랜스파일)
- JSZip (NovelAI 응답 ZIP 해제)
- IndexedDB (캐릭터/프롬프트/세션/잡 영속화)
- File System Access API (출력 폴더 핸들)

서비스 계층(`novelaiGenerate`, `runner`, `db`, 파일 저장기)을 분리해 추후 **Tauri 2** 패키징으로 옮기기 쉽게 구성.

## 보안

- API 토큰은 `localStorage`에 저장되며, 로그/메타데이터/세션 매니페스트에는 포함되지 않음
- UI 표기는 항상 마스킹(`pst-xxxx...xxxx`)
- 토큰 검증 실패(401/403)는 즉시 큐 중단

## 알려진 한계

- Firefox는 File System Access API 미지원
- 토큰은 브라우저 `localStorage` (OS 보안 저장소 사용은 Tauri 패키징 시 추가 예정)
- NovelAI 요청 파라미터는 모델/시기에 따라 달라질 수 있어, 실패 시 페이로드 검토 필요

## 라이선스

미정 (개인 사용 목적).
