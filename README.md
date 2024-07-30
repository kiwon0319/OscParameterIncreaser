# OSC Parameter Increaser (OSCPI)

## Base
파라미터 크기 제한이 없는 로컬 파라미터를 네트워크에 동기화 시킵니다.

## Features
* 1초 주기로 시트에 있는 파라미터의 값을 동기화.
* 시트에 있는파라미터 값이 변경되었을 경우 즉시 해당 파라미터 값을 동기화.
* 마지막 파라미터 값을 시트에 저장 (월드 이동 및 재접속, 아바타 변경시 파라미터 수치 유지)

## Use parameters
파라미터 이름 | 타입 | Sync | 용도
:---: | :---: | :---: | :---
OSCPI/id | Int | Synced | 파라미터 식별
OSCPI/out/float | Float | Synced | Float 타입 파라미터 동기에 사용
OSCPI/out/int | Int | Synced | Int 타입 파라미터 동기에 사용
OSCPI/out/bool | Bool | Synced | Bool 타입 파라미터 동기에 사용
OSCPI/out/light | Float | Synced | Light 모드 사용시 타입에 상관없이 파라미터 동기에 사용
OSCPI/reset | Bool | local | 파라미터들의 값을 기본값으로 초기화

## UNITY SETUP
1. VRC 파라미터
   * 기존 파라미터들의 Sync 체크해제
   * 위 항목을 참고하여 파라미터 추가 (이하 OSCPI 파라미터)


2. 애니메이터
   * 기존 VRC 파라미터와 동일한 이름의 애니메이터 파라미터 이름을 VRC파라미터랑 다르게 변경 (EX: Costume -> out/Coustume)
   * 애니메이터 파라미터에 OSCPI 파라미터 추가
   * 동기화를 위한 새로운 레이어 생성 (이하 Sync 레이어)


3. Sync 레이어
   * OSCPI/id 의 값에 따라서 분기
   * 분기된 노드에 VRC Avatar Parameter Driver 추가
   * Add 버튼을 누른 뒤, Type은 Copy, Source는 시트 참조해서 id 에 맞는 기존 VRC 파라미터로 설정, destination은 이에 대응하는 애니메이터 파라미터로 변경

  
4. 사용할 파라미터 수 만큼 3 항목 반복
