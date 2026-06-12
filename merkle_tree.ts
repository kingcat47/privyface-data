/**
 * Poseidon Hash를 사용한 머클 트리 생성 스크립트
 * o1js를 사용하여 머클 트리를 생성합니다.
 */

import { Field, Poseidon } from 'o1js';
import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';

interface MerkleProof {
  leaf_index: number;
  leaf_hash: string;
  pathElements: string[];
  pathIndices: number[];
  parentIndex: number;
}

interface MerkleTreeResult {
  merkle_root: string;
  leaf_count: number;
  tree_levels: number;
  proofs: MerkleProof[];
}

interface TreeLevel {
  hashes: string[];
  names: string[];
}

function extractNameFromFilename(filename: string): string {
  const name = path.parse(filename).name;
  const nameMapping: Record<string, string> = {
    taegyeum: '이태겸',
    yuchan: '한유찬',
    wonyung: '곽원영',
    chaenuo: '차은우',
  };
  const nameLower = name.toLowerCase();
  for (const [key, value] of Object.entries(nameMapping)) {
    if (nameLower.includes(key)) {
      return value;
    }
  }
  return name;
}

function poseidonHashPair(left: string, right: string): string {
  const leftField = Field(left);
  const rightField = Field(right);
  const hash = Poseidon.hash([leftField, rightField]);
  return hash.toString();
}

function buildMerkleTree(leafHashes: string[], imageNames: string[]): {
  root: string;
  tree: TreeLevel[];
  proofs: MerkleProof[];
} {
  if (leafHashes.length === 0) {
    throw new Error('리프 노드가 비어있습니다.');
  }

  const tree: TreeLevel[] = [
    { hashes: [...leafHashes], names: imageNames.map(extractNameFromFilename) },
  ];
  let currentLevel: TreeLevel = {
    hashes: [...leafHashes],
    names: imageNames.map(extractNameFromFilename),
  };

  console.log('\n' + '='.repeat(60));
  console.log('머클 트리 노드별 해시값');
  console.log('='.repeat(60));

  // 리프 노드 출력
  console.log('\n[레벨 0 - 리프 노드]');
  for (let i = 0; i < currentLevel.hashes.length; i++) {
    console.log(`${currentLevel.names[i]}: ${currentLevel.hashes[i]}`);
  }

  let level = 1;

  // 리프에서 루트까지 상향식으로 트리 구성
  while (currentLevel.hashes.length > 1) {
    const nextLevel: TreeLevel = { hashes: [], names: [] };

    // 짝수 개수로 맞추기 (홀수면 마지막 노드를 복제)
    if (currentLevel.hashes.length % 2 === 1) {
      currentLevel.hashes.push(currentLevel.hashes[currentLevel.hashes.length - 1]);
      currentLevel.names.push(currentLevel.names[currentLevel.names.length - 1]);
    }

    console.log(`\n[레벨 ${level} - 부모 노드]`);

    // 두 개씩 묶어서 부모 노드 생성
    for (let i = 0; i < currentLevel.hashes.length; i += 2) {
      const left = currentLevel.hashes[i];
      const right = currentLevel.hashes[i + 1];

      // 부모 노드 이름 생성
      let parentName: string;
      if (level === 1) {
        const leftName = currentLevel.names[i];
        const rightName = currentLevel.names[i + 1];
        parentName = `부모(${leftName},${rightName})`;
      } else {
        const leftName = currentLevel.names[i];
        const rightName = currentLevel.names[i + 1];
        parentName = `부모(${leftName},${rightName})`;
      }

      const parentHash = poseidonHashPair(left, right);
      nextLevel.hashes.push(parentHash);
      nextLevel.names.push(parentName);

      console.log(`${parentName}: ${parentHash}`);
    }

    tree.push(nextLevel);
    currentLevel = nextLevel;
    level++;
  }

  // 머클 루트는 마지막 레벨의 유일한 노드
  const merkleRoot = currentLevel.hashes[0];

  console.log(`\n[머클 루트]`);
  console.log(`머클루트: ${merkleRoot}`);
  console.log('='.repeat(60));

  // 각 리프에 대한 머클 증명 생성
  const proofs: MerkleProof[] = [];
  for (let leafIndex = 0; leafIndex < leafHashes.length; leafIndex++) {
    const proof = generateMerkleProof(leafIndex, tree);
    proofs.push(proof);
  }

  return {
    root: merkleRoot,
    tree,
    proofs,
  };
}

function generateMerkleProof(
  leafIndex: number,
  tree: TreeLevel[]
): MerkleProof {
  const pathElements: string[] = [];
  const pathIndices: number[] = [];
  let currentIndex = leafIndex;
  let parentIndex: number | null = null;

  // 리프에서 루트까지 올라가면서 증명 수집
  for (let level = 0; level < tree.length - 1; level++) {
    const currentLevel = tree[level];
    const nextLevel = tree[level + 1];

    // 형제 노드 찾기
    let siblingIndex: number;
    if (currentIndex % 2 === 0) {
      siblingIndex = currentIndex + 1;
      pathIndices.push(0); // Hash(현재, 형제)
    } else {
      siblingIndex = currentIndex - 1;
      pathIndices.push(1); // Hash(형제, 현재)
    }

    // 형제 노드 추가
    if (siblingIndex < currentLevel.hashes.length) {
      pathElements.push(currentLevel.hashes[siblingIndex]);
    } else {
      // 형제가 없으면 자신을 복제 (홀수 개수 처리)
      pathElements.push(currentLevel.hashes[currentIndex]);
    }

    // 부모 노드 찾기
    const parentIdx = Math.floor(currentIndex / 2);
    if (parentIdx < nextLevel.hashes.length) {
      pathElements.push(nextLevel.hashes[parentIdx]);

      // 첫 번째 레벨의 부모 인덱스 저장
      if (level === 0) {
        parentIndex = parentIdx;
      }

      // 부모의 형제 노드 찾기
      let parentSiblingIndex: number;
      if (parentIdx % 2 === 0) {
        parentSiblingIndex = parentIdx + 1;
      } else {
        parentSiblingIndex = parentIdx - 1;
      }

      if (parentSiblingIndex < nextLevel.hashes.length) {
        pathElements.push(nextLevel.hashes[parentSiblingIndex]);
      }
      // 부모의 형제가 없으면 추가하지 않음 (None 값 제거)
    }

    // 다음 레벨로 이동
    currentIndex = parentIdx;
  }

  return {
    leaf_index: leafIndex,
    leaf_hash: tree[0].hashes[leafIndex],
    pathElements,
    pathIndices,
    parentIndex: parentIndex ?? 0,
  };
}

function main() {
  console.log('='.repeat(60));
  console.log('Poseidon Hash 기반 머클 트리 생성');
  console.log('='.repeat(60));

  // CSV 파일 읽기
  const csvFile = 'government_face_data_all.csv';
  if (!fs.existsSync(csvFile)) {
    console.error(`오류: ${csvFile} 파일을 찾을 수 없습니다.`);
    console.error('먼저 face_analysis.py를 실행하여 이미지를 분석하세요.');
    process.exit(1);
  }

  const csvContent = fs.readFileSync(csvFile, 'utf-8');
  const records = parse(csvContent, {
    columns: true,
    skip_empty_lines: true,
  });

  // 리프 노드 해시값 추출 (CSV 순서대로)
  const leafHashes: string[] = [];
  const imageNames: string[] = [];

  for (const record of records) {
    leafHashes.push(String(record.face_hash));
    imageNames.push(String(record.image_name));
  }

  console.log(`\n리프 노드 개수: ${leafHashes.length}`);
  console.log('\n리프 노드 해시값:');
  for (let i = 0; i < leafHashes.length; i++) {
    console.log(`  [${i}] ${imageNames[i]}: ${leafHashes[i].substring(0, 20)}...`);
  }

  // 머클 트리 구성
  const merkleTree = buildMerkleTree(leafHashes, imageNames);

  // 결과를 파일로 저장
  const outputFile = 'merkle_tree_result.json';
  const result: MerkleTreeResult = {
    merkle_root: merkleTree.root,
    leaf_count: leafHashes.length,
    tree_levels: merkleTree.tree.length,
    proofs: merkleTree.proofs,
  };

  fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf-8');

  console.log(`\n✅ 결과가 저장되었습니다: ${outputFile}`);
  console.log(`✅ 머클 루트: ${merkleTree.root}`);
}

if (require.main === module) {
  main();
}

