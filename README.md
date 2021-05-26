# Kiwoom API Hanlder
키움증권 Open API+ ActiveX Control을 Python에서 사용할 수 있도록 만든 package입니다.

---
### Installation

``` sh
# easy install with pip
pip install kiwoom_api_handler
```

or

``` sh
# You can check the latest sources with the command
git clone https://github.com/DonghyungKo/kiwoom_api_handler.git
```

### Requirements

**1. python 3.6 or higher (32bit)**
  > 키움증권 OPEN API+는 32bit 환경에서만 실행 가능하므로, 기존 64bit 환경을 이용하는
  경우에는 32bit 가상환경을 생성하여야 합니다.

 ``` sh
 # Anaconda Prompt에서 32bit 가상환경을 생성하는 방법
 # 1. 관리자 권한으로 Anaconda Prompt를 실행
 set CONDA_FORCE_32BIT=1
 conda create -n py36_32 python=3.6 anaconda

# 설치 후
 conda activate py36_32
 ```

**2. 필수 패키지 설치**
```sh
pip install -r requirements.txt
```

**[3. Kiwoom API+ 다운로드 및 자동 로그인 설정](https://www3.kiwoom.com/nkw.templateFrameSet.do?m=m1408000000)**

---

### kiwoom_api.api.Kiwoom
키움증권 OPEN API+ ActiveX Control의 함수와 이벤트를 관리하는 class입니다.

데이터 수신 및 주문집행과 관련된 클래스의 생성자의 매개변수로 Kiwoom 클래스의 instance를 받습니다.

---
### kiwoom_api.api.DataFeeder
Data 수신과 관련된 기능을 담당하는 class 입니다. **생성자의 매개변수로 Kiwoom 인스턴스(instance)를 받습니다.**

#### 현재까지 요청 가능한 TR 목록

TR과 관련된 자세한 사항은 [키움증권 공식 OPEN API+ 개발
문서](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf) 혹은 KOA StudioSA를 참조하시길 바랍니다.

 - `OPT10004 : 주식호가요청`
 - `OPT10005 : 주식일주월시분요청`
 - `OPT10059 : 종목별투자자기관별요청`
 - `OPT10074 : 일자별실현손익요청`
 - `OPT10075 : 실시간미체결요청`
 - `OPT10080 : 주식분봉차트조회요청`
 - `OPTKWFID : 관심종목정보요청`
 - `OPW00001 : 예수금상세현황요청`
 - `OPW00004 : 계좌평가잔고내역요청`
 - `OPW00007 : 계좌별주문체결내역상세요청`

#### Test Code
```python
import sys
from PyQt5.QtWidgets import QApplication
from kiwoom_api_handler import Kiwoom, DataFeeder

if __name__ == "__main__":

    app = QApplication(sys.argv)

    kiwoom = Kiwoom() # Kiwoom 인스턴스 생성
    kiwoom.commConnect() # API 접속
    feeder = DataFeeder(kiwoom)

    code = "005930" # 삼성전자

    # TR요청(request)에 필요한 parameter는 KOAStudio를 참고하시길 바랍니다.
    # OPT10004: 주식호가요청
    params = {"종목코드": code}
    data = feeder.request(trCode="OPT10004", **params)

    # OPT10059: 종목별투자자기관별요청
    params = {
            "일자": "202003013",
            "종목코드": code,
            "금액수량구분": "1",  # 1:금액, 2:수량
            "매매구분": "0",  # 0:순매수, 1:매수, 2:매도
            "단위구분": "1",  # 1:단주, 1000:천주
        }
    data = feeder.request(trCode='OPT10059', **params)

    # OPTKWFID: 관심종목정보요청 
    # ※ 예외적으로 requestOPTKWIFID 메서드를 호출
    params = {
            "arrCode": "005930;023590", # 종목코드를 ;로 구분
            "next": 0, # 0 연속조회여부 (0: x)
            "codeCount": 2, # 종목코드 갯수
    }
    data = feeder.request(**params)
```

### kiwoom_api.api.Executor

주문 정보(order specification) 생성 및 제출과 관련된 기능을 담당하는 class입니다. **생성자의 매개변수로 Kiwoom 인스턴스(instance)를 받습니다.**

#### Test Code
```python
import sys
from PyQt5.QtWidgets import QApplication
from kiwoom_api_handler import Kiwoom, DataFeeder, Executor

if __name__ == "__main__":

    app = QApplication(sys.argv)

    kiwoom = Kiwoom() # Kiwoom 인스턴스 생성
    kiwoom.commConnect() # API 접속

    feeder = DataFeeder(kiwoom)
    executor = Executor(kiwoom)

    accNo = feeder.getAccNo()
    code = "005930" # 삼성전자

    orderSpecDict = executor.createOrderSpec(
        rqName="test",
        scrNo="0000",
        accNo=accNo,
        orderType=1,  # 신규매수
        code=code,
        qty=1,
        price=0, # 시장가 주문은 가격을 입력하지 않음
        hogaType="03", # "00":지정가, "03":시장가
        originOrderNo="",
    )

     executor.sendOrder(**orderSpecDict) # 삼성전자 1주 신규매수(시장가) 주문 제출
```

#### Help and Future Support
Please leave an issue if you find a bug or need future supports.

you can also contact koko8624@gmail.com for support and bug report.
