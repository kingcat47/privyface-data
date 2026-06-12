"""
얼굴 특징점 분석 및 해시 생성 스크립트
MediaPipe를 사용하여 얼굴 특징점을 추출하고 기하학적 특징을 계산합니다.
"""

import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import pandas as pd
import os
import sys
import urllib.request
import subprocess
import json
import glob

# 모델 파일 다운로드 함수
def download_model():
    """face_landmarker.task 모델 파일을 다운로드합니다."""
    model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    model_path = "face_landmarker.task"
    
    if not os.path.exists(model_path):
        print(f"모델 파일을 다운로드 중입니다: {model_url}")
        try:
            urllib.request.urlretrieve(model_url, model_path)
            print("모델 다운로드 완료!")
        except Exception as e:
            print(f"모델 다운로드 실패: {e}")
            print("수동으로 다운로드하세요:")
            print(f"  {model_url}")
            sys.exit(1)
    else:
        print(f"모델 파일이 이미 존재합니다: {model_path}")
    
    return model_path

# 이미지 파일 자동 찾기
def get_image_paths():
    """user-face 폴더에서 모든 이미지 파일을 자동으로 찾습니다."""
    # user-face 폴더 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_face_dir = os.path.join(script_dir, 'user-face')
    
    # 지원하는 이미지 확장자
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
    
    # user-face 폴더에서 이미지 파일 찾기
    image_files = []
    for ext in image_extensions:
        # 소문자 확장자로 검색 (Windows는 대소문자 구분 안 함)
        found_files = glob.glob(os.path.join(user_face_dir, ext))
        image_files.extend(found_files)
    
    # 중복 제거 (Windows에서 대소문자 구분 안 함으로 인한 중복 방지)
    # 정규화된 경로를 사용하여 중복 제거
    image_files = list(set([os.path.normpath(f) for f in image_files]))
    
    if not image_files:
        print(f"오류: user-face 폴더에서 이미지 파일을 찾을 수 없습니다.")
        print(f"폴더 경로: {user_face_dir}")
        sys.exit(1)
    
    # 파일명으로 정렬
    image_files.sort()
    
    return image_files

# 거리 계산 함수
def get_dist(df, idx1, idx2):
    """두 특징점 사이의 유클리드 거리를 계산합니다."""
    p1 = df[df['Index'] == idx1][['X', 'Y']].values[0]
    p2 = df[df['Index'] == idx2][['X', 'Y']].values[0]
    return np.sqrt(np.sum((p1 - p2)**2))

# Poseidon hash 계산 함수 (JavaScript 호출)
def calculate_poseidon_hash(scaled_features):
    """CircomJS를 사용하여 Poseidon hash를 계산합니다."""
    script_path = os.path.join(os.path.dirname(__file__), 'poseidon_hash.js')
    
    # 특징값 배열을 JSON 문자열로 변환
    features_json = json.dumps(scaled_features)
    
    try:
        # Node.js 스크립트 실행
        # Windows 인코딩 문제 해결을 위해 UTF-8 명시
        result = subprocess.run(
            ['node', script_path, features_json],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"오류: Poseidon hash 계산 실패")
        print(f"stderr: {e.stderr}")
        print("\nNode.js와 circomlibjs가 설치되어 있는지 확인하세요:")
        print("  npm install")
        sys.exit(1)
    except FileNotFoundError:
        print("오류: Node.js가 설치되어 있지 않습니다.")
        print("Node.js를 설치하고 npm install을 실행하세요.")
        sys.exit(1)

# 단일 이미지 처리 함수
def process_image(image_path, detector):
    """단일 이미지를 분석하고 결과를 반환합니다."""
    image_name = os.path.basename(image_path)
    print(f"\n{'='*50}")
    print(f"이미지 분석 중: {image_name}")
    print(f"{'='*50}")
    
    # 이미지 로드 및 분석
    image = mp.Image.create_from_file(image_path)
    detection_result = detector.detect(image)
    
    if not detection_result.face_landmarks:
        print(f"⚠️  얼굴 인식 실패: {image_name}에서 얼굴을 찾을 수 없습니다.")
        return None
    
    img_raw = cv2.imread(image_path)
    h, w, _ = img_raw.shape
    landmarks = detection_result.face_landmarks[0]
    
    # 특징점 좌표 데이터프레임화
    landmarks_data = [[idx, lm.x * w, lm.y * h, lm.z] for idx, lm in enumerate(landmarks)]
    df = pd.DataFrame(landmarks_data, columns=['Index', 'X', 'Y', 'Z'])
    
    # 거리 계산 함수 (데이터프레임을 인자로 받도록 수정)
    def get_dist_wrapper(idx1, idx2):
        return get_dist(df, idx1, idx2)
    
    # --- 10가지 기하학적 특징 추출 (변별력 강화) ---
    dist_eyes = get_dist_wrapper(33, 263)   # 기준점: 눈 사이 거리
    
    features = {
        "f1_nose_len": get_dist_wrapper(1, 4) / dist_eyes,
        "f2_mouth_width": get_dist_wrapper(61, 291) / dist_eyes,
        "f3_eye_to_chin": get_dist_wrapper(1, 152) / dist_eyes,
        "f4_eye_to_mouth": get_dist_wrapper(1, 13) / dist_eyes,
        "f5_nose_width": get_dist_wrapper(102, 331) / dist_eyes,
        "f6_inner_eye_dist": get_dist_wrapper(133, 362) / dist_eyes,
        "f7_eyebrow_dist": get_dist_wrapper(105, 334) / dist_eyes,
        "f8_face_width": get_dist_wrapper(234, 454) / dist_eyes,
        "f9_jaw_width": get_dist_wrapper(58, 288) / dist_eyes,
        "f10_upper_lip": get_dist_wrapper(0, 13) / dist_eyes
    }
    
    # --- ZKP 대응을 위한 정수화 (Scaling) ---
    # 소수점 데이터를 Circom에서 쓰기 위해 10,000을 곱해 정수로 만듭니다.
    scaled_features = [int(val * 10000) for val in features.values()]
    
    # --- 암호화 처리 (Poseidon Hash) ---
    # CircomJS를 사용하여 Poseidon hash 계산
    face_hash = calculate_poseidon_hash(scaled_features)
    
    print("\n[원본 특징 데이터 (Private Input용)]")
    print(f"아래 배열을 나중에 앱의 '정부 데이터'로 사용하세요:")
    print(scaled_features)
    
    print(f"\n[정부 DB 저장용 해시 (Public Input)]")
    print(face_hash)
    
    return {
        'image_name': image_name,
        'image_path': image_path,
        'features': features,
        'scaled_features': scaled_features,
        'face_hash': face_hash
    }

# 메인 실행 함수
def main():
    print("="*50)
    print("얼굴 특징점 분석 및 해시 생성")
    print("="*50)
    
    # 모델 다운로드
    model_path = download_model()
    
    # 이미지 파일 경로들 가져오기
    image_files = get_image_paths()
    print(f"\n발견된 이미지 파일: {len(image_files)}개")
    for img_file in image_files:
        print(f"  - {os.path.basename(img_file)}")
    
    # MediaPipe 모델 설정
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        num_faces=1
    )
    detector = vision.FaceLandmarker.create_from_options(options)
    
    # 모든 이미지 처리
    results = []
    for image_path in image_files:
        result = process_image(image_path, detector)
        if result:
            results.append(result)
    
    if not results:
        print("\n❌ 모든 이미지에서 얼굴 인식에 실패했습니다.")
        sys.exit(1)
    
    # 결과 저장
    print(f"\n{'='*50}")
    print("결과 저장 중...")
    print(f"{'='*50}")
    
    # 각 이미지별로 개별 CSV 파일 저장
    for result in results:
        image_name = result['image_name']
        base_name = os.path.splitext(image_name)[0]
        output_file = f'government_face_data_{base_name}.csv'
        
        df_final = pd.DataFrame([result['features']])
        df_final['image_name'] = image_name
        df_final['face_hash'] = result['face_hash']
        df_final['scaled_features'] = [result['scaled_features']]
        df_final.to_csv(output_file, index=False)
        print(f"✓ {image_name} → {output_file}")
    
    # 전체 결과를 하나의 CSV 파일로도 저장
    if len(results) > 1:
        all_results = []
        for result in results:
            row = result['features'].copy()
            row['image_name'] = result['image_name']
            row['face_hash'] = result['face_hash']
            row['scaled_features'] = str(result['scaled_features'])
            all_results.append(row)
        
        df_all = pd.DataFrame(all_results)
        output_file_all = 'government_face_data_all.csv'
        df_all.to_csv(output_file_all, index=False)
        print(f"✓ 전체 결과 → {output_file_all}")
    
    print(f"\n✅ 총 {len(results)}개의 이미지 분석 완료!")

if __name__ == "__main__":
    main()

