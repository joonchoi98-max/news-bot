"""
STX 2023년 재무상태표 분석 스크립트
DART OpenAPI 활용
"""

import requests
import json
import sys
from datetime import datetime

API_KEY = "dc580e107667376e839049810d78e96a7a99d03f"
BASE_URL = "https://opendart.fss.or.kr/api"

# STX 주요 상장사 corp_code (DART 기준)
STX_COMPANIES = {
    "에스티엑스": "00366781",       # STX (011810)
    "STX엔진": "00104856",          # STX엔진 (077970)
    "STX중공업": "00113671",        # STX중공업 (067250)
}

TARGET_CORP = "에스티엑스"
TARGET_CORP_CODE = STX_COMPANIES[TARGET_CORP]
BSNS_YEAR = "2023"
REPRT_CODE = "11011"  # 사업보고서 (연간)


def fetch_financial_statement(corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "CFS") -> dict:
    """DART API로 재무제표 조회 (CFS=연결, OFS=별도)"""
    url = f"{BASE_URL}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_balance_sheet(data: dict) -> list[dict]:
    """재무상태표(BS) 항목만 추출"""
    if data.get("status") != "000":
        raise ValueError(f"API 오류: {data.get('status')} - {data.get('message')}")
    items = data.get("list", [])
    return [item for item in items if item.get("sj_div") == "BS"]


def fmt_amount(val_str: str) -> str:
    """금액 문자열을 읽기 쉽게 포맷 (원 단위 → 억원)"""
    try:
        val = int(val_str.replace(",", "").replace(" ", ""))
        billions = val / 1_0000_0000
        if abs(billions) >= 1:
            return f"{billions:,.1f}억원"
        else:
            return f"{val:,}원"
    except (ValueError, AttributeError):
        return val_str or "N/A"


def get_value(items: list[dict], account_nm: str, thstrm: bool = True) -> str:
    """계정명으로 당기(thstrm) 또는 전기(frmtrm) 금액 조회"""
    key = "thstrm_amount" if thstrm else "frmtrm_amount"
    for item in items:
        if account_nm in item.get("account_nm", ""):
            return item.get(key, "N/A")
    return "N/A"


def analyze_balance_sheet(bs_items: list[dict]) -> dict:
    """재무상태표 핵심 지표 계산"""
    def val(nm):
        raw = get_value(bs_items, nm)
        try:
            return int(raw.replace(",", "").replace(" ", ""))
        except Exception:
            return 0

    total_assets = val("자산총계")
    current_assets = val("유동자산")
    non_current_assets = val("비유동자산")
    total_liabilities = val("부채총계")
    current_liabilities = val("유동부채")
    non_current_liabilities = val("비유동부채")
    total_equity = val("자본총계")

    ratios = {}

    # 부채비율 = 부채총계 / 자본총계 × 100
    if total_equity != 0:
        ratios["부채비율"] = f"{total_liabilities / total_equity * 100:.1f}%"
    else:
        ratios["부채비율"] = "N/A"

    # 유동비율 = 유동자산 / 유동부채 × 100
    if current_liabilities != 0:
        ratios["유동비율"] = f"{current_assets / current_liabilities * 100:.1f}%"
    else:
        ratios["유동비율"] = "N/A"

    # 자기자본비율 = 자본총계 / 자산총계 × 100
    if total_assets != 0:
        ratios["자기자본비율"] = f"{total_equity / total_assets * 100:.1f}%"
    else:
        ratios["자기자본비율"] = "N/A"

    return {
        "total_assets": total_assets,
        "current_assets": current_assets,
        "non_current_assets": non_current_assets,
        "total_liabilities": total_liabilities,
        "current_liabilities": current_liabilities,
        "non_current_liabilities": non_current_liabilities,
        "total_equity": total_equity,
        "ratios": ratios,
    }


def print_report(bs_items: list[dict], analysis: dict):
    """분석 결과 출력"""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  STX(에스티엑스) 2023년 재무상태표 분석")
    print(f"  기준: 연결재무제표 | 단위: 억원")
    print(f"  분석일: {datetime.today().strftime('%Y-%m-%d')}")
    print(sep)

    # 주요 계정 출력 (당기/전기 비교)
    key_accounts = [
        ("자산총계",        "▶ 자산총계"),
        ("유동자산",        "  ├ 유동자산"),
        ("비유동자산",      "  └ 비유동자산"),
        ("부채총계",        "▶ 부채총계"),
        ("유동부채",        "  ├ 유동부채"),
        ("비유동부채",      "  └ 비유동부채"),
        ("자본총계",        "▶ 자본총계"),
    ]

    print(f"\n{'항목':<20} {'당기(2023)':>15} {'전기(2022)':>15}")
    print("-" * 52)
    for account_nm, label in key_accounts:
        curr = fmt_amount(get_value(bs_items, account_nm, thstrm=True))
        prev = fmt_amount(get_value(bs_items, account_nm, thstrm=False))
        print(f"{label:<22} {curr:>15} {prev:>15}")

    # 재무 비율
    print(f"\n{'─' * 52}")
    print("▶ 주요 재무 비율")
    print(f"{'─' * 52}")
    ratios = analysis["ratios"]
    print(f"  부채비율         {ratios['부채비율']:>10}   (100% 이하 우량)")
    print(f"  유동비율         {ratios['유동비율']:>10}   (200% 이상 우량)")
    print(f"  자기자본비율     {ratios['자기자본비율']:>10}   (50% 이상 우량)")

    # 종합 평가
    print(f"\n{'─' * 52}")
    print("▶ 종합 평가")
    print(f"{'─' * 52}")

    total_assets = analysis["total_assets"]
    total_liabilities = analysis["total_liabilities"]
    total_equity = analysis["total_equity"]

    debt_ratio_val = (total_liabilities / total_equity * 100) if total_equity else 0
    current_ratio_val = (
        (analysis["current_assets"] / analysis["current_liabilities"] * 100)
        if analysis["current_liabilities"] else 0
    )
    equity_ratio_val = (total_equity / total_assets * 100) if total_assets else 0

    comments = []
    if debt_ratio_val > 200:
        comments.append(f"  ⚠ 부채비율 {debt_ratio_val:.0f}%로 재무 레버리지가 높아 재무 위험이 있습니다.")
    elif debt_ratio_val > 100:
        comments.append(f"  - 부채비율 {debt_ratio_val:.0f}%로 보통 수준입니다.")
    else:
        comments.append(f"  ✓ 부채비율 {debt_ratio_val:.0f}%로 재무구조가 안정적입니다.")

    if current_ratio_val < 100:
        comments.append(f"  ⚠ 유동비율 {current_ratio_val:.0f}%로 단기 유동성 위험이 있습니다.")
    elif current_ratio_val < 150:
        comments.append(f"  - 유동비율 {current_ratio_val:.0f}%로 단기 유동성이 보통 수준입니다.")
    else:
        comments.append(f"  ✓ 유동비율 {current_ratio_val:.0f}%로 단기 유동성이 양호합니다.")

    if equity_ratio_val < 30:
        comments.append(f"  ⚠ 자기자본비율 {equity_ratio_val:.0f}%로 자기자본이 취약합니다.")
    elif equity_ratio_val < 50:
        comments.append(f"  - 자기자본비율 {equity_ratio_val:.0f}%로 보통 수준입니다.")
    else:
        comments.append(f"  ✓ 자기자본비율 {equity_ratio_val:.0f}%로 자기자본이 충실합니다.")

    for c in comments:
        print(c)

    print(f"\n{sep}\n")


def save_raw_data(bs_items: list[dict], filename: str = "stx_bs_2023.json"):
    """원시 데이터 JSON 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(bs_items, f, ensure_ascii=False, indent=2)
    print(f"[완료] 원시 데이터 저장: {filename}")


def main():
    print(f"[조회 중] {TARGET_CORP} 2023년 재무상태표 (DART API)...")

    # 1. 연결 재무제표 시도
    try:
        data = fetch_financial_statement(TARGET_CORP_CODE, BSNS_YEAR, REPRT_CODE, fs_div="CFS")
        bs_items = extract_balance_sheet(data)
        fs_label = "연결"
    except Exception as e:
        print(f"[경고] 연결재무제표 조회 실패 ({e}), 별도재무제표 시도...")
        try:
            data = fetch_financial_statement(TARGET_CORP_CODE, BSNS_YEAR, REPRT_CODE, fs_div="OFS")
            bs_items = extract_balance_sheet(data)
            fs_label = "별도"
        except Exception as e2:
            print(f"[오류] 재무제표 조회 실패: {e2}")
            sys.exit(1)

    if not bs_items:
        print("[오류] 재무상태표 데이터가 없습니다.")
        sys.exit(1)

    print(f"[완료] {fs_label}재무제표 {len(bs_items)}개 항목 조회 완료")

    analysis = analyze_balance_sheet(bs_items)
    print_report(bs_items, analysis)
    save_raw_data(bs_items)


if __name__ == "__main__":
    main()
