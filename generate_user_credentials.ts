/**
 * 사용자별 신원 증명(Identity Credential) JSON 파일 생성 스크립트
 * 실제 이미지 분석 결과를 기반으로 각 사용자의 신원 정보를 생성합니다.
 */

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
  proofs: MerkleProof[];
}

interface UserCredential {
  userId: number;
  userName: string;
  identityData: {
    features: number[];
    featureHash: string;
  };
  merkleProof: {
    root: string;
    pathElements: string[];
    pathIndices: number[];
    leafIndex: number;
    parentIndex: number;
  };
  issuedAt: string;
}

function extractNameFromFilename(filename: string): string {
  const name = path.parse(filename).name;
  const nameMapping: Record<string, string> = {
    taegyeum: '이태겸',
    yuchan: '한유찬',
    wonyung: '곽원영',
    chaenuo: '차은우',
    bojungyuchan: '한유찬',
    chaletgo: '차은우',
    privyface_ltg: '이태겸',
    qwakwon: '곽원영',
  };
  const nameLower = name.toLowerCase();
  for (const [key, value] of Object.entries(nameMapping)) {
    if (nameLower.includes(key)) {
      return value;
    }
  }
  return name;
}

function parseScaledFeatures(featuresStr: string): number[] {
  try {
    return JSON.parse(featuresStr);
  } catch {
    // 문자열 형태의 리스트 파싱 시도
    const cleaned = featuresStr.replace(/[\[\]]/g, '');
    return cleaned.split(',').map((x) => parseInt(x.trim(), 10));
  }
}

function generateUserCredential(
  userId: number,
  imageName: string,
  features: number[],
  featureHash: string,
  proof: MerkleProof,
  merkleRoot: string
): UserCredential {
  const userName = extractNameFromFilename(imageName);
  const issuedAt = new Date().toISOString();

  return {
    userId,
    userName,
    identityData: {
      features,
      featureHash,
    },
    merkleProof: {
      root: merkleRoot,
      pathElements: proof.pathElements,
      pathIndices: proof.pathIndices,
      leafIndex: proof.leaf_index,
      parentIndex: proof.parentIndex,
    },
    issuedAt,
  };
}

function main() {
  console.log('='.repeat(60));
  console.log('사용자 신원 증명 파일 생성');
  console.log('='.repeat(60));

  // 실제 이미지 분석 결과 로드
  console.log('\n이미지 분석 결과 로드 중...');
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

  // 머클 트리 결과 로드
  console.log('머클 트리 결과 로드 중...');
  const resultFile = 'merkle_tree_result.json';
  if (!fs.existsSync(resultFile)) {
    console.error(`오류: ${resultFile} 파일을 찾을 수 없습니다.`);
    console.error('먼저 merkle_tree.ts를 실행하여 머클 트리를 생성하세요.');
    process.exit(1);
  }

  const merkleResult: MerkleTreeResult = JSON.parse(
    fs.readFileSync(resultFile, 'utf-8')
  );
  const merkleRoot = merkleResult.merkle_root;
  const proofs = merkleResult.proofs;

  // 출력 디렉토리 생성
  const outputDir = 'user-credentials';
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log(`\n머클 루트: ${merkleRoot}`);
  console.log(`분석된 이미지 수: ${records.length}`);
  console.log(`출력 디렉토리: ${outputDir}/`);
  console.log('\n' + '-'.repeat(60));

  // 각 사용자별로 신원 증명 생성
  const allCredentials: UserCredential[] = [];

  for (let idx = 0; idx < records.length; idx++) {
    const record = records[idx];
    const userId = idx;

    // CSV에서 데이터 추출
    const imageName = String(record.image_name);
    const faceHash = String(record.face_hash);
    const features = parseScaledFeatures(String(record.scaled_features));

    // 해당 해시값의 머클 증명 찾기
    let proof: MerkleProof | null = null;
    for (const p of proofs) {
      if (p.leaf_hash === faceHash) {
        proof = p;
        break;
      }
    }

    if (!proof) {
      console.log(
        `⚠️  경고: ${imageName}의 해시값에 대한 머클 증명을 찾을 수 없습니다.`
      );
      console.log(`  해시: ${faceHash.substring(0, 30)}...`);
      continue;
    }

    // 신원 증명 생성
    const credential = generateUserCredential(
      userId,
      imageName,
      features,
      faceHash,
      proof,
      merkleRoot
    );
    allCredentials.push(credential);

    // 개별 파일로 저장
    const filename = `user_${userId}_${credential.userName}.json`;
    const filepath = path.join(outputDir, filename);

    fs.writeFileSync(
      filepath,
      JSON.stringify(credential, null, 2),
      'utf-8'
    );

    console.log(
      `✓ [${userId}] ${imageName} → ${credential.userName} → ${filename}`
    );
    console.log(
      `  - Features: ${credential.identityData.features.length}개`
    );
    console.log(
      `  - Path Elements: ${credential.merkleProof.pathElements.length}개`
    );
    console.log(`  - Path Indices: ${credential.merkleProof.pathIndices}`);
    console.log(`  - Parent Index: ${credential.merkleProof.parentIndex}`);
  }

  // 전체 결과를 하나의 파일로도 저장
  const allFilepath = path.join(outputDir, 'all_users.json');
  fs.writeFileSync(
    allFilepath,
    JSON.stringify(allCredentials, null, 2),
    'utf-8'
  );

  console.log('\n' + '='.repeat(60));
  console.log(
    `✅ 총 ${allCredentials.length}개의 사용자 신원 증명 파일 생성 완료!`
  );
  console.log(`✅ 전체 결과: ${allFilepath}`);
  console.log('='.repeat(60));
}

if (require.main === module) {
  main();
}

