
import streamlit as st
import os
from pathlib import Path

# PDF 파싱용, 필요시 선택 사용
import fitz  # PyMuPDF
import pdfplumber

# 구글 Gemini API
import google.generativeai as genai

# 환경변수 또는 st.secrets에서 API Key 불러오기
from dotenv import load_dotenv

# 스타일 커스터마이징 (Blue/White 톤)
st.set_page_config(page_title="학업성적관리 규정/수행평가 점검 컨설팅", page_icon=":blue_book:", layout="wide")
custom_css = '''
    <style>
        body, .stApp { background-color: #f7fbff; }
        .stButton>button { background-color: #2471a3; color: white; }
        .stFileUploader { background-color: #eaf2fb; }
        .stTable { background-color: white; }
        h1, h2, h3, h4 { color: #2471a3; }
    </style>
'''
st.markdown(custom_css, unsafe_allow_html=True)

# API KEY 설정 (app.py와 같은 폴더: .env 또는 key.env)
_APP_DIR = Path(__file__).resolve().parent
for _env_name in (".env", "key.env"):
    load_dotenv(_APP_DIR / _env_name)
api_key = os.getenv("GEMINI_API_KEY", None) or os.getenv("GOOGLE_API_KEY", None)
# 예: gemini-2.5-flash, gemini-2.5-pro (https://ai.google.dev/gemini-api/docs/models)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else None
    except Exception:
        api_key = None
if not api_key:
    st.warning("`.env` 또는 `key.env`, 또는 secrets에 GEMINI_API_KEY를 설정하세요.")
else:
    genai.configure(api_key=api_key)
    # 추후 Gemini 사용 코드 삽입

# 상위 지침: 배포 시 서버(저장소)에 포함된 PDF만 사용. 로컬 테스트용 업로드는 ALLOW_UPPER_PDF_UPLOAD=1
_raw_upper = os.getenv("UPPER_GUIDANCE_PDF", "data/upper_guidelines.pdf")
UPPER_GUIDANCE_PATH = Path(_raw_upper)
if not UPPER_GUIDANCE_PATH.is_absolute():
    UPPER_GUIDANCE_PATH = (_APP_DIR / _raw_upper).resolve()
ALLOW_UPPER_UPLOAD = os.getenv("ALLOW_UPPER_PDF_UPLOAD", "").lower() in ("1", "true", "yes")

st.title("학교 학업성적관리 규정/수행평가 점검 컨설팅")
st.caption(
    "학교 자체 규정·교과 수행평가 계획 PDF를 올리면, 배포된 상위 지침과 비교·점검합니다."
)

st.markdown("#### **문서**")

if ALLOW_UPPER_UPLOAD:
    st.caption("로컬 모드: 상위 지침도 직접 업로드할 수 있습니다.")
    col1, col2, col3 = st.columns(3)
    with col1:
        upper_pdf = st.file_uploader("상위 지침/체크리스트 PDF", type=["pdf"], key="upper")
    with col2:
        school_pdf = st.file_uploader("학교 자체 규정 PDF", type=["pdf"], key="school")
    with col3:
        subj_pdf = st.file_uploader("교과별 수행평가 계획 PDF", type=["pdf"], key="subject")
else:
    upper_pdf = None
    with st.container():
        st.markdown("**상위 지침·체크리스트** (관리자 배포본)")
        if UPPER_GUIDANCE_PATH.is_file():
            st.success(f"적용 중: `{UPPER_GUIDANCE_PATH.name}`")
        else:
            st.warning(
                f"파일이 없습니다: `{UPPER_GUIDANCE_PATH}`. "
                "GitHub/Streamlit 배포 전에 이 경로에 PDF를 넣거나, 환경변수 `UPPER_GUIDANCE_PDF`로 경로를 지정하세요."
            )
    st.markdown("**사용자 업로드**")
    col2, col3 = st.columns(2)
    with col2:
        school_pdf = st.file_uploader("학교 자체 규정 PDF", type=["pdf"], key="school")
    with col3:
        subj_pdf = st.file_uploader("교과별 수행평가 계획 PDF", type=["pdf"], key="subject")


def extract_text_from_pdf_path(path: Path) -> str:
    text = ""
    if not path.is_file():
        return ""
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= 5:
                    break
                text += (page.extract_text() or "") + "\n"
    except Exception:
        try:
            with fitz.open(path) as doc:
                for i, page in enumerate(doc):
                    if i >= 5:
                        break
                    text += (page.get_text() or "") + "\n"
        except Exception:
            pass
    return text


def extract_text_from_pdf(file):
    # PyMuPDF 또는 pdfplumber로 텍스트 추출 (임시: 첫 5p 만)
    text = ""
    if file:
        try:
            with pdfplumber.open(file) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i>=5: break
                    text += (page.extract_text() or "") + "\n"
        except Exception:
            file.seek(0)
            with fitz.open(stream=file.read(), filetype="pdf") as doc:
                for i, page in enumerate(doc):
                    if i>=5: break
                    text += (page.get_text() or "") + "\n"
    return text

if st.button("AI 분석 실행", use_container_width=True, type="primary"):
    with st.spinner("PDF 파일 파싱 중..."):
        if ALLOW_UPPER_UPLOAD:
            upper_text = extract_text_from_pdf(upper_pdf)
        else:
            upper_text = extract_text_from_pdf_path(UPPER_GUIDANCE_PATH)
        school_text = extract_text_from_pdf(school_pdf)
        subj_text = extract_text_from_pdf(subj_pdf)

    if ALLOW_UPPER_UPLOAD and not upper_pdf:
        st.warning("상위 지침 PDF를 업로드하세요.")
    elif not ALLOW_UPPER_UPLOAD and not UPPER_GUIDANCE_PATH.is_file():
        st.error(
            "배포된 상위 지침 PDF가 없습니다. `data/upper_guidelines.pdf`를 넣거나 "
            "환경변수 `UPPER_GUIDANCE_PDF`로 경로를 지정하세요."
        )
    else:
        # 예시: Gemini 프롬프트 준비 및 API 호출 (구체 구현은 별도 함수로 분리 가능)
        prompt = f"""
    [상위지침/체크리스트]
    {upper_text}

    [학교규정]
    {school_text}

    [교과별 수행평가]
    {subj_text}

    위 내용을 바탕으로
    - 상위지침과 학교규정의 누락/충돌/수정점 찾기(수정안, 근거조항, 권장문구 제시)
    - 수행평가계획의 성취기준 반영 및 공정/객관성 체크
    통합 점검테이블과 요약 리포트(한국어)로 작성해줘!
    """

        if api_key:
            try:
                model = genai.GenerativeModel(GEMINI_MODEL)
                response = model.generate_content(prompt)
                try:
                    result = response.text
                except ValueError:
                    result = None
                if result:
                    st.success("AI 분석 완료!")
                    # 임시: 결과 나누어 표시 (향후 테이블 분리 파싱)
                    st.markdown("### 점검 결과")
                    st.markdown(result)
                else:
                    st.warning("Gemini 응답이 비어 있거나 차단·필터에 걸렸을 수 있습니다.")
            except Exception as e:
                st.error(f"Gemini API 오류: {e}")
        else:
            st.error(
                "API 키가 읽히지 않아 분석을 실행할 수 없습니다. "
                "`app.py`와 같은 폴더에 `.env` 또는 `key.env`를 두고 "
                "`GEMINI_API_KEY=발급받은키` 한 줄을 넣은 뒤 "
                "**Rerun**으로 다시 실행하세요."
            )

st.markdown("---")
st.info(
    "**보안:** 사용자가 업로드한 학교 규정·수행평가 파일은 서버에 저장하지 않으며, "
    "분석 후 세션에서만 사용됩니다. 상위 지침은 앱과 함께 배포된 파일을 읽습니다."
)
