# PrivyFace Data Pipeline (ogui)

얼굴 사진으로부터 ZKP(영지식 증명) 기반 신원 인증에 필요한 데이터를 생성하는 **오프라인 전처리 파이프라인**입니다.

## 전체 시스템 구성

PrivyFace는 3개의 레포지토리로 구성됩니다.

```
[ogui] (이 레포)              [privyface]                  [privyface-backend]
오프라인 데이터 생성   →   React 웹앱 (얼굴 스캔 + ZKP 생성)   →   NestJS 서버 (ZKP 검증)
정부 DB 역할 시뮬레이션        디바이스에서만 얼굴 처리              실제 얼굴 데이터 수신 없음
```

- **[privyface](https://github.com/kingcat47/privyface)**: 웹캠으로 얼굴을 스캔하고 ZK Proof를 생성하는 React 프론트엔드
- **[privyface-backend](https://github.com/kingcat47/privyface-backend)**: Merkle Proof와 ZK Proof를 검증하는 NestJS 백엔드

## 이 레포의 역할

실제 서비스에서 "정부 DB"에 해당하는 데이터를 사전에 생성합니다.

```
얼굴 사진 (user-face/)
    ↓
MediaPipe로 10가지 기하학적 특징 추출
    ↓
Poseidon Hash 생성 (ZK-SNARK 친화적 해시)
    ↓
Merkle Tree 구성
    ↓
사용자별 Credential JSON 생성 (user-credentials/)
    ↓
privyface 프론트엔드에서 "정부 데이터"로 사용
```

## 왜 ZKP인가?

```
일반 인증: 얼굴 데이터를 서버로 전송 → 생체정보 유출 위험
ZKP 인증:  "나는 등록된 사람임"을 수학적으로 증명 → 실제 얼굴 데이터는 디바이스 밖으로 나가지 않음
```

- **Private Input** (본인만 보유): 얼굴 기하학적 특징값 10개
- **Public Input** (공개 가능): Poseidon Hash, Merkle Root
- 서버는 ZK Proof만 검증하고 실제 생체정보는 수신하지 않습니다.

## 추출하는 10가지 얼굴 특징

모든 값은 눈 사이 거리로 정규화한 비율값입니다.

| 특징 | 설명 |
|------|------|
| f1_nose_len | 코 길이 |
| f2_mouth_width | 입 너비 |
| f3_eye_to_chin | 눈~턱 거리 |
| f4_eye_to_mouth | 눈~입 거리 |
| f5_nose_width | 코 너비 |
| f6_inner_eye_dist | 눈 사이 내측 거리 |
| f7_eyebrow_dist | 눈썹 사이 거리 |
| f8_face_width | 얼굴 너비 |
| f9_jaw_width | 턱 너비 |
| f10_upper_lip | 윗입술 높이 |

비율값에 10,000을 곱해 정수화합니다 (Circom ZKP 회로 호환).

## 설치

Python 패키지:

```bash
pip install -r requirements.txt
```

Node.js 패키지 (Poseidon hash용):

```bash
npm install
```

**요구사항**: Python 3.7+, Node.js 14+

MediaPipe 모델 파일은 최초 실행 시 자동 다운로드됩니다.

## 사용 방법

### 1단계: 얼굴 분석 및 해시 생성

분석할 이미지를 `user-face/` 폴더에 넣고 실행합니다.

```bash
python face_analysis.py
```

지원 형식: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`

출력:
- `government_face_data_{이미지명}.csv`: 이미지별 특징값 + Poseidon Hash
- `government_face_data_all.csv`: 전체 통합 결과

### 2단계: Merkle Tree 생성

```bash
python merkle_tree.py
```

출력: `merkle_tree_result.json`

### 3단계: 사용자 Credential 생성

```bash
python generate_user_credentials.py
```

출력: `user-credentials/` 폴더에 사용자별 JSON 파일

생성된 JSON 구조:

```json
{
  "userId": 0,
  "userName": "홍길동",
  "identityData": {
    "features": [735, 5351, 8600, ...],
    "featureHash": "138263..."
  },
  "merkleProof": {
    "root": "40415...",
    "pathElements": [...],
    "pathIndices": [1, 0]
  }
}
```

이 JSON을 privyface 프론트엔드의 "정부 데이터"로 사용합니다.

## .gitignore 권장 설정

실제 얼굴 사진과 생체 데이터는 절대 커밋하지 마세요.

```
user-face/
user-credentials/
government_face_data_*.csv
government_face_data_all.csv
merkle_tree_result.json
face_landmarker.task
```

## 기술 스택

- **얼굴 인식**: MediaPipe Face Landmarker (468개 랜드마크)
- **해시 함수**: Poseidon Hash via [o1js](https://github.com/o1-labs/o1js) (Mina Protocol)
- **데이터 처리**: Python (NumPy, OpenCV, Pandas)
