// 아두이노 연결 테스트 - LED 블링크
// Arduino Nano 내장 LED (13번 핀) 사용

void setup() {
  // 13번 핀을 출력으로 설정
  pinMode(LED_BUILTIN, OUTPUT);
  
  // 시리얼 통신 시작 (옵션 - 연결 확인용)
  Serial.begin(9600);
  Serial.println("Arduino Connected!");
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);  // LED 켜기
  Serial.println("LED ON");
  delay(500);                       // 1초 대기
  
  digitalWrite(LED_BUILTIN, LOW);   // LED 끄기
  Serial.println("LED OFF");
  delay(200);                       // 1초 대기
}