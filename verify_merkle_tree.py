"""
머클 트리 검증 스크립트
주어진 노드 해시값들로부터 머클 루트를 계산하고 검증합니다.
"""

import subprocess
import json
import os
from typing import List

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
    inputs = [left, right]
    return calculate_poseidon_hash(inputs)


def verify_merkle_root(
    taegyeum_hash: str,
    chaenuo_hash: str,
    parent_wonyung_yuchan_hash: str,
    expected_root: str
) -> bool:
    """
    주어진 노드 해시값들로부터 머클 루트를 계산하고 검증합니다.
    
    Args:
        taegyeum_hash: 이태겸 노드 해시값
        chaenuo_hash: 차은우 노드 해시값
        parent_wonyung_yuchan_hash: 부모(곽원영,한유찬) 해시값
        expected_root: 기대하는 머클 루트 해시값
    
    Returns:
        검증 성공 여부 (True/False)
    """
    print("="*60)
    print("머클 트리 검증")
    print("="*60)
    
    print("\n[입력값]")
    print(f"이태겸: {taegyeum_hash}")
    print(f"차은우: {chaenuo_hash}")
    print(f"부모(곽원영,한유찬): {parent_wonyung_yuchan_hash}")
    print(f"기대 머클루트: {expected_root}")
    
    print("\n" + "-"*60)
    print("[계산 과정]")
    print("-"*60)
    
    # 1단계: 이태겸과 차은우를 결합하여 부모(차은우,이태겸) 생성
    print("\n1단계: 부모(차은우,이태겸) 계산")
    print(f"  입력: [차은우, 이태겸]")
    print(f"    차은우: {chaenuo_hash}")
    print(f"    이태겸: {taegyeum_hash}")
    
    parent_chaenuo_taegyeum = poseidon_hash_pair(chaenuo_hash, taegyeum_hash)
    print(f"  결과: 부모(차은우,이태겸) = {parent_chaenuo_taegyeum}")
    
    # 2단계: 부모(차은우,이태겸)와 부모(곽원영,한유찬)를 결합하여 머클루트 생성
    print("\n2단계: 머클루트 계산")
    print(f"  입력: [부모(차은우,이태겸), 부모(곽원영,한유찬)]")
    print(f"    부모(차은우,이태겸): {parent_chaenuo_taegyeum}")
    print(f"    부모(곽원영,한유찬): {parent_wonyung_yuchan_hash}")
    
    calculated_root = poseidon_hash_pair(parent_chaenuo_taegyeum, parent_wonyung_yuchan_hash)
    print(f"  결과: 머클루트 = {calculated_root}")
    
    # 3단계: 검증
    print("\n" + "="*60)
    print("[검증 결과]")
    print("="*60)
    
    is_valid = calculated_root == expected_root
    
    print(f"계산된 머클루트: {calculated_root}")
    print(f"기대 머클루트:   {expected_root}")
    print(f"\n검증 결과: {'✅ 성공' if is_valid else '❌ 실패'}")
    
    if not is_valid:
        print("\n⚠️  경고: 계산된 머클루트가 기대값과 일치하지 않습니다!")
    
    return is_valid


def main():
    # 터미널 출력에서 가져온 실제 해시값들
    taegyeum_hash = "13826367653508464817569990927844063827730313223437176853991177462728835083818"
    chaenuo_hash = "10094362218276815648174033054262866975703745050504857247488483499092523696968"
    parent_wonyung_yuchan_hash = "20039212002287728841204099158317516386554265240404598122970150388400882795400"
    expected_root = "4041534543159854687984238186366163703328051953185635023444461187988033966095"
    
    # 검증 실행
    is_valid = verify_merkle_root(
        taegyeum_hash=taegyeum_hash,
        chaenuo_hash=chaenuo_hash,
        parent_wonyung_yuchan_hash=parent_wonyung_yuchan_hash,
        expected_root=expected_root
    )
    
    if is_valid:
        print("\n✅ 머클 트리 검증이 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 머클 트리 검증에 실패했습니다.")
        exit(1)


if __name__ == "__main__":
    main()

