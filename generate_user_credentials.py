"""
사용자별 신원 증명(Identity Credential) JSON 파일 생성 스크립트
실제 이미지 분석 결과를 기반으로 각 사용자의 신원 정보를 생성합니다.
"""

import json
import os
import pandas as pd
import ast
from datetime import datetime
from typing import Dict, List

# 이미지 파일명에서 이름 추출 함수
def extract_name_from_filename(filename: str) -> str:
    """이미지 파일명에서 이름을 추출합니다."""
    # 확장자 제거
    name = os.path.splitext(filename)[0]
    
    # 한글 이름 매핑 (파일명 기반)
    name_mapping = {
        "taegyeum": "이태겸",
        "yuchan": "한유찬",
        "wonyung": "곽원영",
        "chaenuo": "차은우",
        "bojungyuchan": "한유찬",
        "chaletgo": "차은우",
        "privyface_ltg": "이태겸",
        "qwakwon": "곽원영",
    }
    
    # 소문자로 변환하여 매핑 확인
    name_lower = name.lower()
    for key, value in name_mapping.items():
        if key in name_lower:
            return value
    
    # 매핑이 없으면 파일명을 그대로 사용
    return name


def load_face_analysis_results() -> pd.DataFrame:
    """face_analysis.py의 결과 CSV를 로드합니다."""
    csv_file = 'government_face_data_all.csv'
    if not os.path.exists(csv_file):
        print(f"오류: {csv_file} 파일을 찾을 수 없습니다.")
        print("먼저 face_analysis.py를 실행하여 이미지를 분석하세요.")
        exit(1)
    
    df = pd.read_csv(csv_file)
    return df


def load_merkle_tree_result() -> Dict:
    """머클 트리 결과 파일을 로드합니다."""
    result_file = 'merkle_tree_result.json'
    if not os.path.exists(result_file):
        print(f"오류: {result_file} 파일을 찾을 수 없습니다.")
        print("먼저 merkle_tree.py를 실행하여 머클 트리를 생성하세요.")
        exit(1)
    
    with open(result_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_user_credential(
    user_id: int,
    image_name: str,
    features: List[int],
    feature_hash: str,
    proof: Dict,
    merkle_root: str
) -> Dict:
    """
    사용자 신원 증명 JSON을 생성합니다.
    
    TypeScript 인터페이스 구조:
    {
      userId: number,
      userName: string,
      identityData: {
        features: number[],
        featureHash: string
      },
      merkleProof: {
        root: string,
        pathElements: string[],
        pathIndices: number[],
        leafIndex: number,
        parentIndex: number
      }
    }
    """
    # 이미지 파일명에서 이름 추출
    user_name = extract_name_from_filename(image_name)
    
    # 현재 시간 (ISO 8601 형식)
    issued_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    credential = {
        "userId": user_id,
        "userName": user_name,
        "identityData": {
            "features": features,
            "featureHash": feature_hash
        },
        "merkleProof": {
            "root": merkle_root,
            "pathElements": proof['pathElements'],
            "pathIndices": proof['pathIndices'],
            "leafIndex": proof['leaf_index'],
            "parentIndex": proof['parentIndex']
        },
        "issuedAt": issued_at
    }
    
    return credential


def main():
    print("="*60)
    print("사용자 신원 증명 파일 생성")
    print("="*60)
    
    # 실제 이미지 분석 결과 로드
    print("\n이미지 분석 결과 로드 중...")
    df = load_face_analysis_results()
    
    # 머클 트리 결과 로드
    print("머클 트리 결과 로드 중...")
    merkle_result = load_merkle_tree_result()
    merkle_root = merkle_result['merkle_root']
    proofs = merkle_result['proofs']
    
    # 출력 디렉토리 생성
    output_dir = 'user-credentials'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n머클 루트: {merkle_root}")
    print(f"분석된 이미지 수: {len(df)}")
    print(f"출력 디렉토리: {output_dir}/")
    print("\n" + "-"*60)
    
    # 각 사용자별로 신원 증명 생성
    all_credentials = []
    
    for idx, row in df.iterrows():
        user_id = idx  # CSV의 인덱스를 사용자 ID로 사용
        
        # CSV에서 데이터 추출
        image_name = row['image_name']
        face_hash = str(row['face_hash'])
        
        # scaled_features 파싱 (문자열로 저장된 리스트)
        scaled_features_str = row['scaled_features']
        if isinstance(scaled_features_str, str):
            # 문자열 형태의 리스트를 실제 리스트로 변환
            try:
                features = ast.literal_eval(scaled_features_str)
            except:
                # JSON 형태일 수도 있음
                features = json.loads(scaled_features_str)
        else:
            features = scaled_features_str
        
        # 해당 해시값의 머클 증명 찾기
        proof = None
        for p in proofs:
            if p['leaf_hash'] == face_hash:
                proof = p
                break
        
        if not proof:
            print(f"⚠️  경고: {image_name}의 해시값에 대한 머클 증명을 찾을 수 없습니다.")
            print(f"  해시: {face_hash[:30]}...")
            continue
        
        # 신원 증명 생성
        credential = generate_user_credential(
            user_id=user_id,
            image_name=image_name,
            features=features,
            feature_hash=face_hash,
            proof=proof,
            merkle_root=merkle_root
        )
        all_credentials.append(credential)
        
        # 개별 파일로 저장
        filename = f"user_{user_id}_{credential['userName']}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(credential, f, indent=2, ensure_ascii=False)
        
        print(f"✓ [{user_id}] {image_name} → {credential['userName']} → {filename}")
        print(f"  - Features: {len(credential['identityData']['features'])}개")
        print(f"  - Path Elements: {len(credential['merkleProof']['pathElements'])}개")
        print(f"  - Path Indices: {credential['merkleProof']['pathIndices']}")
        print(f"  - Parent Index: {credential['merkleProof']['parentIndex']}")
    
    # 전체 결과를 하나의 파일로도 저장
    all_filepath = os.path.join(output_dir, 'all_users.json')
    with open(all_filepath, 'w', encoding='utf-8') as f:
        json.dump(all_credentials, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print(f"✅ 총 {len(all_credentials)}개의 사용자 신원 증명 파일 생성 완료!")
    print(f"✅ 전체 결과: {all_filepath}")
    print("="*60)


if __name__ == "__main__":
    main()

