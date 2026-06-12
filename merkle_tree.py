"""
Poseidon Hash를 사용한 머클 트리 생성 스크립트
백엔드 검증 코드와 호환되는 머클 트리 구조 생성
"""

import subprocess
import json
import os
import pandas as pd
from typing import List, Dict

def calculate_poseidon_hash(inputs: List[str]) -> str:
    """CircomJS를 사용하여 Poseidon hash를 계산합니다."""
    script_path = os.path.join(os.path.dirname(__file__), 'poseidon_hash.js')
    
    # 입력값을 JSON 배열로 변환
    inputs_json = json.dumps(inputs)
    
    try:
        # Node.js 스크립트 실행
        result = subprocess.run(
            ['node', script_path, inputs_json],
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
        raise
    except FileNotFoundError:
        print("오류: Node.js가 설치되어 있지 않습니다.")
        raise


def poseidon_hash_pair(left: str, right: str) -> str:
    """두 해시값을 결합하여 새로운 Poseidon hash를 생성합니다."""
    # 백엔드: Poseidon.hash([left, right])
    inputs = [left, right]
    return calculate_poseidon_hash(inputs)


def extract_name_from_filename(filename: str) -> str:
    """이미지 파일명에서 이름을 추출합니다."""
    import os
    name = os.path.splitext(filename)[0]
    name_mapping = {
        "taegyeum": "이태겸",
        "yuchan": "한유찬",
        "wonyung": "곽원영",
        "chaenuo": "차은우",
    }
    name_lower = name.lower()
    for key, value in name_mapping.items():
        if key in name_lower:
            return value
    return name


def build_merkle_tree(leaf_hashes: List[str], image_names: List[str] = None) -> Dict:
    """
    리프 노드 해시값들로부터 머클 트리를 구성합니다.
    
    Returns:
        {
            'root': str,
            'tree': List[List[str]],  # 각 레벨의 노드들
            'proofs': List[Dict]  # 각 리프에 대한 머클 증명
        }
    """
    if not leaf_hashes:
        raise ValueError("리프 노드가 비어있습니다.")
    
    # 트리 구조: 각 레벨의 노드들을 저장
    tree = [leaf_hashes.copy()]  # 레벨 0: 리프 노드들
    current_level = leaf_hashes.copy()
    level_names = [image_names.copy() if image_names else [f"리프{i}" for i in range(len(leaf_hashes))]]
    
    print("\n" + "="*60)
    print("머클 트리 노드별 해시값")
    print("="*60)
    
    # 리프 노드 출력
    print("\n[레벨 0 - 리프 노드]")
    for i, hash_val in enumerate(leaf_hashes):
        name = extract_name_from_filename(image_names[i]) if image_names else f"리프{i}"
        print(f"{name}: {hash_val}")
    
    level = 1
    
    # 리프에서 루트까지 상향식으로 트리 구성
    while len(current_level) > 1:
        next_level = []
        next_level_names = []
        
        # 짝수 개수로 맞추기 (홀수면 마지막 노드를 복제)
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
            if image_names:
                level_names[-1].append(level_names[-1][-1])
        
        print(f"\n[레벨 {level} - 부모 노드]")
        
        # 두 개씩 묶어서 부모 노드 생성
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            
            # 부모 노드 이름 생성
            if level == 1:
                left_name = extract_name_from_filename(image_names[i]) if image_names else f"리프{i}"
                right_name = extract_name_from_filename(image_names[i + 1]) if image_names else f"리프{i+1}"
                parent_name = f"부모({left_name},{right_name})"
            else:
                left_name = level_names[-1][i] if level_names else f"노드{i}"
                right_name = level_names[-1][i + 1] if level_names else f"노드{i+1}"
                parent_name = f"부모({left_name},{right_name})"
            
            parent_hash = poseidon_hash_pair(left, right)
            next_level.append(parent_hash)
            next_level_names.append(parent_name)
            
            print(f"{parent_name}: {parent_hash}")
        
        tree.append(next_level)
        level_names.append(next_level_names)
        current_level = next_level
        level += 1
    
    # 머클 루트는 마지막 레벨의 유일한 노드
    merkle_root = current_level[0]
    
    print(f"\n[머클 루트]")
    print(f"머클루트: {merkle_root}")
    print("="*60)
    
    # 각 리프에 대한 머클 증명 생성
    proofs = []
    for leaf_index in range(len(leaf_hashes)):
        proof = generate_merkle_proof(leaf_index, tree)
        proofs.append(proof)
    
    return {
        'root': merkle_root,
        'tree': tree,
        'proofs': proofs
    }


def generate_merkle_proof(leaf_index: int, tree: List[List[str]]) -> Dict:
    """
    특정 리프 노드에 대한 머클 증명을 생성합니다.
    
    백엔드 검증 코드 구조:
    - pathElements: [형제노드, 부모노드, 부모의형제노드]
    - pathIndices: [0 또는 1] - 0이면 Hash(현재, 형제), 1이면 Hash(형제, 현재)
    - parentIndex: 부모 노드의 인덱스
    
    Returns:
        {
            'leaf_index': int,
            'leaf_hash': str,
            'pathElements': List[str],  # [형제, 부모, 부모의형제]
            'pathIndices': List[int],  # [0 또는 1]
            'parentIndex': int
        }
    """
    path_elements = []
    path_indices = []
    current_index = leaf_index
    parent_index = None
    
    # 리프에서 루트까지 올라가면서 증명 수집
    for level in range(len(tree) - 1):
        current_level = tree[level]
        next_level = tree[level + 1]
        
        # 형제 노드 찾기
        if current_index % 2 == 0:
            sibling_index = current_index + 1
            path_indices.append(0)  # Hash(현재, 형제)
        else:
            sibling_index = current_index - 1
            path_indices.append(1)  # Hash(형제, 현재)
        
        # 형제 노드 추가
        if sibling_index < len(current_level):
            path_elements.append(current_level[sibling_index])
        else:
            # 형제가 없으면 자신을 복제 (홀수 개수 처리)
            path_elements.append(current_level[current_index])
        
        # 부모 노드 찾기
        parent_idx = current_index // 2
        if parent_idx < len(next_level):
            path_elements.append(next_level[parent_idx])
            
            # 첫 번째 레벨의 부모 인덱스 저장
            if level == 0:
                parent_index = parent_idx
            
            # 부모의 형제 노드 찾기
            if parent_idx % 2 == 0:
                parent_sibling_index = parent_idx + 1
            else:
                parent_sibling_index = parent_idx - 1
            
            if parent_sibling_index < len(next_level):
                path_elements.append(next_level[parent_sibling_index])
            else:
                # 부모의 형제가 없으면 None (루트 레벨)
                path_elements.append(None)
        else:
            path_elements.append(None)
            path_elements.append(None)
        
        # 다음 레벨로 이동
        current_index = parent_idx
    
    # None 값 제거
    path_elements = [elem for elem in path_elements if elem is not None]
    
    return {
        'leaf_index': leaf_index,
        'leaf_hash': tree[0][leaf_index],
        'pathElements': path_elements,
        'pathIndices': path_indices,
        'parentIndex': parent_index if parent_index is not None else 0
    }


def main():
    print("="*60)
    print("Poseidon Hash 기반 머클 트리 생성")
    print("="*60)
    
    # 실제 이미지 분석 결과에서 해시값 추출
    csv_file = 'government_face_data_all.csv'
    if not os.path.exists(csv_file):
        print(f"오류: {csv_file} 파일을 찾을 수 없습니다.")
        print("먼저 face_analysis.py를 실행하여 이미지를 분석하세요.")
        exit(1)
    
    df = pd.read_csv(csv_file)
    
    # 리프 노드 해시값 추출 (CSV 순서대로)
    leaf_hashes = [str(row['face_hash']) for _, row in df.iterrows()]
    image_names = [row['image_name'] for _, row in df.iterrows()]
    
    print(f"\n리프 노드 개수: {len(leaf_hashes)}")
    print("\n리프 노드 해시값:")
    for i, (image_name, hash_val) in enumerate(zip(image_names, leaf_hashes)):
        print(f"  [{i}] {image_name}: {hash_val[:20]}...")
    
    # 머클 트리 구성
    merkle_tree = build_merkle_tree(leaf_hashes, image_names)
    
    # 결과를 파일로 저장
    output_file = 'merkle_tree_result.json'
    result = {
        'merkle_root': merkle_tree['root'],
        'leaf_count': len(leaf_hashes),
        'tree_levels': len(merkle_tree['tree']),
        'proofs': merkle_tree['proofs']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 결과가 저장되었습니다: {output_file}")
    print(f"✅ 머클 루트: {merkle_tree['root']}")


if __name__ == "__main__":
    main()

