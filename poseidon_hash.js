/**
 * Poseidon Hash 계산 스크립트
 * o1js를 사용하여 특징값 배열에 대한 Poseidon hash를 생성합니다.
 */

const { Field, Poseidon } = require("o1js");

// 명령줄 인자로부터 특징값 배열 받기
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error("오류: 특징값 배열이 필요합니다.");
  console.error("사용법: node poseidon_hash.js [값1,값2,값3,...]");
  process.exit(1);
}

try {
  // 입력값 파싱 (JSON 배열 또는 쉼표로 구분된 값)
  let inputArray;
  if (args[0].startsWith("[")) {
    // JSON 배열 형식
    inputArray = JSON.parse(args[0]);
  } else {
    // 쉼표로 구분된 값
    inputArray = args[0].split(",").map((x) => x.trim());
  }

  // Field 배열로 변환
  const fieldArray = inputArray.map((x) => Field(x));

  // Poseidon hash 계산
  const hash = Poseidon.hash(fieldArray);

  // Field Element를 문자열로 변환 (10진수 거대 정수)
  const hashString = hash.toString();
  console.log(hashString);
} catch (error) {
  console.error("오류:", error.message);
  process.exit(1);
}
