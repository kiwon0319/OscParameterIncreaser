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
