import streamlit as st
import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai
import anthropic
import re

# ==========================================
# 1. 국가법령 Open API 연동 클래스
# ==========================================
class LawAPIHandler:
    def __init__(self):
        self.oc_key = "243400"  # 발급받으신 인증키
        self.search_url = "https://www.law.go.kr/DRF/lawSearch.do"
        self.detail_url = "https://www.law.go.kr/DRF/lawService.do"

    def get_law_articles(self, law_name, keyword):
        """1. 법령 조문 검색 (전체 법령 대응)"""
        params = {"OC": self.oc_key, "target": "law", "type": "XML", "query": law_name}
        matched = []
        try:
            res = requests.get(self.search_url, params=params)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            law_item = root.find('.//law')
            if law_item is not None:
                mst = law_item.find('법령일련번호').text
                full_name = law_item.find('법령명한글').text
                
                detail_params = {"OC": self.oc_key, "target": "law", "MST": mst, "type": "XML"}
                detail_res = requests.get(self.detail_url, params=detail_params)
                detail_res.encoding = 'utf-8'
                detail_root = ET.fromstring(detail_res.text)
                
                for article in detail_root.findall('.//조문단위'):
                    content = article.find('조문내용').text if article.find('조문내용') is not None else ""
                    # 키워드가 조문 내용에 포함되어 있거나, 키워드와 법령명이 같으면(전체조회) 추가
                    if keyword in content or law_name == keyword:
                        art_no = article.find('조문번호').text if article.find('조문번호') is not None else ""
                        art_title = article.find('조문제목').text if article.find('조문제목') is not None else ""
                        matched.append(f"📜 **{full_name} {art_no} ({art_title})**\n\n> {content.strip()}")
        except:
            pass
        return matched

    def get_precedents(self, query):
        """2. 대법원 및 하급심 판례 검색"""
        params = {"OC": self.oc_key, "target": "prec", "type": "XML", "query": query}
        results = []
        try:
            res = requests.get(self.search_url, params=params)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            for item in root.findall('.//prec'):
                name = item.find('사건명').text if item.find('사건명') is not None else ""
                num = item.find('사건번호').text if item.find('사건번호') is not None else ""
                court = item.find('법원명').text if item.find('법원명') is not None else ""
                date = item.find('선고일자').text if item.find('선고일자') is not None else ""
                link = item.find('판례상세링크').text if item.find('판례상세링크') is not None else ""
                
                full_link = f"https://www.law.go.kr{link}" if link else "#"
                results.append(f"⚖️ **{name}**\n\n* **사건번호:** {num} ({court} / 선고일자: {date})\n* 🔗 [판례 원문 보기]({full_link})")
        except:
            pass
        return results

    def get_admin_rules(self, query):
        """3. 부칙, 예규, 고시, 지침(행정규칙) 검색"""
        params = {"OC": self.oc_key, "target": "admr", "type": "XML", "query": query}
        results = []
        try:
            res = requests.get(self.search_url, params=params)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            for item in root.findall('.//admr'):
                name = item.find('행정규칙명').text if item.find('행정규칙명') is not None else ""
                dept = item.find('소관부처명').text if item.find('소관부처명') is not None else ""
                num = item.find('발령번호').text if item.find('발령번호') is not None else ""
                link = item.find('행정규칙상세링크').text if item.find('행정규칙상세링크') is not None else ""
                
                full_link = f"https://www.law.go.kr{link}" if link else "#"
                results.append(f"📋 **{name}**\n\n* **소관부처:** {dept} (발령번호: {num})\n* 🔗 [지침/예규 원문 보기]({full_link})")
        except:
            pass
        return results

# ==========================================
# 2. [혁신] 제한 없는 5,000개 법령 유니버설 파서
# ==========================================
def parse_query_rules(user_query):
    """API 키가 없을 때 문장을 분리하여 모든 법령명과 키워드를 동적 매칭"""
    q = user_query.strip()
    
    # 부동산/세무 숏컷 규칙 (편의용 유지)
    q_clean = q.replace(" ", "")
    if any(k in q_clean for k in ["복비", "중개보수", "수수료", "초과"]): return "공인중개사법", "중개보수"
    if any(k in q_clean for k in ["전세", "임차권", "묵시적"]): return "주택임대차보호법", "임차권"
    if "양도" in q_clean: return "소득세법", "양도"
    if "취득" in q_clean: return "지방세법", "취득"
    if "종부" in q_clean: return "종합부동산세법", "종합부동산"
    
    # 💡 [핵심] 띄어쓰기 기준 자동 분리 규칙 적용
    # 입력 예: "민법 해제", "형법 사기", "부동산등기법 신청"
    words = q.split()
    if len(words) >= 2:
        return words[0], words[1]
    
    # 단어 하나만 입력한 경우 (예: "민법" 입력 시 법령명 민법, 키워드 민법으로 조문 전체 대기)
    return words[0], words[0]

# ==========================================
# 3. AI 모델 통합 처리부
# ==========================================
def parse_query_with_ai(user_query, active_llm, api_key):
    prompt = f"질문을 분석해 가장 적합한 대한민국 법령명과 조문 검색어 1개를 뽑아주세요. 정확한 법률 명칭 명명이 핵심입니다.\n형식:\n법령명: [정확한 법률이름]\n키워드: [단어]\n질문: {user_query}"
    try:
        if active_llm == "Claude":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=150, temperature=0, messages=[{"role": "user", "content": prompt}])
            text = response.content[0].text
        elif active_llm == "Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            text = response.text

        law_match = re.search(r"법령명:\s*(.+)", text)
        keyword_match = re.search(r"키워드:\s*(.+)", text)
        return law_match.group(1).strip(), keyword_match.group(1).strip()
    except:
        return parse_query_rules(user_query)

def generate_canva_design(title: str, summary: str, design_type: str = "presentation") -> str:
    """Canva Connect API를 호출하여 법률 브리핑용 디자인을 실제 생성합니다."""
    # ⚠️ 주의: 상용화 시 Streamlit 세션(OAuth 2.0)을 통해 발급받은 유저의 Access Token을 사용해야 합니다.
    access_token = st.session_state.get("canva_access_token", "YOUR_CANVA_ACCESS_TOKEN")
    
    if access_token == "YOUR_CANVA_ACCESS_TOKEN":
        return "❌ Canva 연동 오류: 유저 인증(Access Token)이 필요합니다."

    url = "https://api.canva.com/rest/v1/designs"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "design_type": {
            "type": "preset",
            "name": design_type  # 예: presentation, doc
        },
        "title": title
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            design_url = response.json().get("design", {}).get("url", "URL 확인 불가")
            return f"✅ '{title}' 디자인이 성공적으로 생성되었습니다. (실제 접속 링크: {design_url})"
        else:
            return f"❌ Canva 디자인 생성 실패: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ Canva 통신 오류 발생: {e}"

def generate_final_answer_with_ai(user_query, target_law, keyword, articles, active_llm, api_key, enable_canva=False):
    context = "\n\n".join(articles) if articles else "관련 구체적 조문 없음"
    prompt = f"참고 조문을 바탕으로 질문에 답하세요. 몇 조 몇 항인지 조항 번호를 명시하고 'Zero Vacancy Briefing' 전문가답게 정중하고 신뢰감 있는 전문가 톤을 유지하세요.\n질문: {user_query}\n법령: {target_law}\n\n[참고 조문]\n{context}"

    if enable_canva:
        prompt += "\n\n[시스템 특별 지시사항] 분석 내용을 바탕으로 시각적인 '카드뉴스'나 '브리핑 PPT'가 필요하다고 판단되거나 사용자가 요청한 경우, 반드시 `generate_canva_design` 도구를 사용하여 디자인을 함께 생성하세요."
        
    try:
        if active_llm == "Claude":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=2000, temperature=0.3, messages=[{"role": "user", "content": prompt}])
            return response.content[0].text
        elif active_llm == "Gemini":
            genai.configure(api_key=api_key)
            tools = [generate_canva_design] if enable_canva else None
            model = genai.GenerativeModel('gemini-2.0-flash', tools=tools)
            response = model.generate_content(prompt)
            
            # 도구 호출(Function Calling) 감지 및 실행 처리
            if response.candidates and response.candidates[0].content.parts:
                parts = response.candidates[0].content.parts
                if any(p.function_call for p in parts):
                    fc = [p.function_call for p in parts if p.function_call][0]
                    if fc.name == "generate_canva_design":
                        args = {k: v for k, v in fc.args.items()}
                        tool_result = generate_canva_design(**args)
                        text_parts = [p.text for p in parts if p.text]
                        base_text = text_parts[0] if text_parts else "분석 결과를 바탕으로 시각 자료를 생성했습니다."
                        return f"{base_text}\n\n🎨 **[Canva 연동] 디자인 자동화 결과**\n{tool_result}"
            return response.text
    except Exception as e:
        return f"최종 답변 생성 중 오류 발생: {e}"

# ==========================================
# 4. [Admin] Canva SCIM API 연동 (사용자 프로비저닝)
# ==========================================
def provision_canva_user(scim_token, email, first_name, last_name):
    """Canva SCIM API를 통해 새로운 팀원(변호사/직원) 계정을 생성합니다."""
    url = "https://www.canva.com/_scim/v2/Users"
    headers = {
        "Authorization": f"Bearer {scim_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": email,
        "name": {
            "givenName": first_name,
            "familyName": last_name
        },
        "emails": [{"primary": True, "value": email}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code, response.json()
    except Exception as e:
        return 500, {"error": str(e)}

# ==========================================
# 4. Streamlit UI 구성
# ==========================================
st.set_page_config(page_title="법무법인 종합 법령 검색기", page_icon="⚖️", layout="centered")
st.title("⚖️ 법무법인 종합 법령·판례·예규 스마트 챗봇")

# 사이드바 설정
st.sidebar.title("🛠️ AI 엔진 설정")
gemini_key = st.sidebar.text_input("구글 Gemini API Key 입력", type="password")
claude_key = st.sidebar.text_input("클로드 Claude API Key 입력", type="password")

active_llm, active_key = None, None
if claude_key.strip():
    active_llm, active_key = "Claude", claude_key.strip()
    st.sidebar.success("🟢 Claude 3.5 엔진 활성화")
elif gemini_key.strip():
    active_llm, active_key = "Gemini", gemini_key.strip()
    st.sidebar.success("🟢 Gemini 2.0 엔진 활성화")
else:
    st.sidebar.info("🔵 키 미입력: [실시간 전천후 직송 모드]")

# ==========================================
# 🎨 Canva MCP 연동 설정
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Canva 디자인 연동 (MCP)")
enable_canva = st.sidebar.checkbox("Canva MCP 커넥터 활성화")
if enable_canva:
    st.sidebar.info("ℹ️ 활성화됨 (실제 상용화 시 개별 유저 Canva 인증 및 Python MCP 클라이언트 적용 필요)")

# 🏢 Canva SCIM 연동 (Admin)
st.sidebar.markdown("---")
st.sidebar.subheader("🏢 Canva 계정 관리 (SCIM/Admin)")
enable_scim = st.sidebar.checkbox("조직원 계정 자동 발급 활성화")
if enable_scim:
    st.sidebar.warning("⚠️ Enterprise 전용: 로펌 내 변호사/직원의 Canva 계정 자동 생성 및 관리용 API입니다.")
    st.sidebar.text_input("SCIM Bearer Token", type="password", key="scim_token")
    if st.sidebar.button("테스트 유저 생성"):
        st.sidebar.info("SCIM API 연동 준비 완료 (provision_canva_user 함수 호출)")

# 📋 [요청 반영] 법무법인 필수 주요 법령 목록 안내판 배치
st.sidebar.markdown("---")
with st.sidebar.expander("📚 법무법인 필수 주요 법령 목록 (조회 가능)", expanded=True):
    st.markdown("""
    **기본 육법 및 소송법**
    * `민법` / `민사소송법` / `민사집행법`
    * `형법` / `형사소송법`
    * `상법` / `부동산등기법`
    
    **부동산 및 특별법**
    * `공인중개사법`
    * `주택임대차보호법`
    * `상가건물 임대차보호법`
    * `집합건물의 소유 및 관리에 관한 법률`
    
    **세법 및 행정법**
    * `소득세법` (양도세 포함)
    * `지방세법` (취득세 포함)
    * `종합부동산세법` / `행정소송법`
    """)

st.sidebar.subheader("💡 키 미입력 모드 검색 가이드")
st.sidebar.info("**[법령이름] [한칸띄고] [키워드]** 구조로 입력 시 5,000개 모든 법령이 실시간 직송됩니다.\n\n예: `민법 해제`\n예: `형법 사기`\n예: `상법 주식회사`")

# API 핸들러 객체 선언
api_handler = LawAPIHandler()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 법무법인 전용 종합 법령 검색 시스템입니다. 질문하시거나 **'[법령명] [키워드]'** 형태로 입력하시면 실시간 조문, 판례, 예규를 통합 검색합니다."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if user_input := st.chat_input("질문 또는 '[법령명] [키워드]'를 입력하세요..."):
    with st.chat_message("user"): st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        if active_llm:
            target_law, keyword = parse_query_with_ai(user_input, active_llm, active_key)
        else:
            target_law, keyword = parse_query_rules(user_input)
        
        with st.spinner(f"정부 법령 서버에서 [{target_law}] 관련 조문+판례+예규 일괄 수집 중..."):
            laws = api_handler.get_law_articles(target_law, keyword)
            precedents = api_handler.get_precedents(user_input)
            admin_rules = api_handler.get_admin_rules(user_input)
            
        st.markdown(f"### 🔎 '{user_input}' 데이터 검색 결과")
        st.caption(f"🎯 타겟팅된 법률명: **{target_law}** | 추출된 조문 키워드: **{keyword}**")
        tab1, tab2, tab3 = st.tabs(["📜 관련 법령 조문", "⚖️ 관련 판례 목록", "📋 지침 · 예규 · 고시"])
        
        with tab1:
            st.write("") # 상단 여백
            if laws:
                for l in laws[:7]: 
                    st.markdown(l)
                    st.divider()
            else:
                st.info(f"[{target_law}] 내에서 '{keyword}' 키워드로 검색된 관련 조항이 없습니다.")
                
        with tab2:
            st.write("") # 상단 여백
            if precedents:
                for p in precedents[:7]: 
                    st.markdown(p)
                    st.divider()
            else:
                st.info(f"'{user_input}'(으)로 검색된 대법원 및 하급심 판례가 없습니다.")
                
        with tab3:
            st.write("") # 상단 여백
            if admin_rules:
                for a in admin_rules[:7]: 
                    st.markdown(a)
                    st.divider()
            else:
                st.info(f"'{user_input}'(으)로 검색된 소관 부처 예규·고시 지침이 없습니다.")

        if active_llm:
            with st.spinner("AI 전문가 종합 브리핑을 작성하는 중..."):
                reply = generate_final_answer_with_ai(user_input, target_law, keyword, laws[:3], active_llm, active_key, enable_canva)
                st.divider()
                st.markdown("### 🤖 AI 전문가 종합 분석\n")
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": f"### 🤖 AI 전문가 종합 분석\n\n{reply}"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": f"✅ '{user_input}' 조회를 완료했습니다. 상단 탭을 확인하세요."})