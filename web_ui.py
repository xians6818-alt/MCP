import os
import json
import hashlib
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from adapters.speech_to_text import create_transcriber
from config import settings
from core.analyzer import Analyzer
from core.copywriter import Copywriter
from core.predictor import Predictor
from core.rubric_engine import RubricEngine
from llm.deepseek_client import DeepSeekClient
from storage.excel_exporter import ExcelExporter
from storage.file_storage import FileStorage
from storage.supabase_storage import SupabaseStorage


APP_NAME = "AI 短视频内容工业化生产台 (Content Engine Pro)"


EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


st.set_page_config(
    page_title="Content Engine Pro",
    page_icon="C",
    layout="wide",
)


def init_clients():
    llm_client = DeepSeekClient(
        settings.MOONSHOT_API_KEY,
        settings.MOONSHOT_BASE_URL,
        settings.MOONSHOT_MODEL,
        settings.LLM_TIMEOUT_SECONDS,
        settings.LLM_MAX_RETRIES,
    )
    rubric_engine = RubricEngine(llm_client)
    analyzer = Analyzer(llm_client)
    predictor = Predictor(rubric_engine, analyzer)
    copywriter = Copywriter(llm_client)
    file_storage = FileStorage(settings.PREDICTIONS_DIR, settings.SCRIPTS_DIR)
    json_storage = SupabaseStorage(settings.STATE_FILE)
    excel_exporter = ExcelExporter(settings.EXPORTS_DIR)
    return rubric_engine, analyzer, predictor, copywriter, file_storage, json_storage, excel_exporter


def inject_style():
    st.markdown(
        """
        <style>
        :root {
            --ink: #17201c;
            --muted: #65736d;
            --line: #dde5df;
            --surface: #fbfcf8;
            --green: #1f6f55;
            --amber: #b66a1e;
            --blue: #315f8a;
        }
        .stApp { background: #f5f7f1; color: var(--ink); }
        section[data-testid="stSidebar"] { background: #111a17; }
        section[data-testid="stSidebar"] * { color: #edf5ee; }
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }
        .topbar {
            display: flex; align-items: center; justify-content: space-between; gap: 20px;
            padding: 22px 26px; border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.9); border-radius: 10px; margin-bottom: 18px;
        }
        .topbar h1 { margin: 0; font-size: 27px; line-height: 1.2; letter-spacing: 0; }
        .topbar p { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
        .badge {
            display: inline-block; padding: 7px 10px; border-radius: 999px;
            background: #e9f2ec; color: #1d654f; font-size: 13px; font-weight: 700;
        }
        .kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
        .kpi { border: 1px solid var(--line); background: #ffffff; border-radius: 8px; padding: 14px 16px; }
        .kpi span { color: var(--muted); font-size: 12px; }
        .kpi strong { display: block; margin-top: 6px; font-size: 24px; color: var(--ink); }
        .section-title { margin: 0 0 10px; font-size: 18px; font-weight: 700; color: var(--ink); }
        .subtle { color: var(--muted); font-size: 13px; }
        div[data-testid="stTabs"] button { font-size: 15px; font-weight: 600; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
        @media (max-width: 900px) { .topbar { display: block; } .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(state: dict):
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <h1>{APP_NAME}</h1>
                <p>面向产品/品牌种草的脚本创作、评分诊断、手机拍摄执行和数据复盘工作台。</p>
            </div>
            <span class="badge">V2.1 Generic</span>
        </div>
        <div class="kpi-row">
            <div class="kpi"><span>Rubric版本</span><strong>{state.get("rubric_version", "v2")}</strong></div>
            <div class="kpi"><span>评估记录</span><strong>{len(state.get("evaluation_records", []))}</strong></div>
            <div class="kpi"><span>预测记录</span><strong>{len(state.get("prediction_records", []))}</strong></div>
            <div class="kpi"><span>校准样本</span><strong>{state.get("calibration_samples", 0)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_dataframe(score_result):
    return pd.DataFrame(
        [
            {"维度": dim, "分数": f"{score}/5", "评分理由": score_result.reasons.get(dim, "")}
            for dim, score in score_result.scores.to_dict().items()
        ]
    )


def storyboard_dataframe(score_result):
    return pd.DataFrame(
        [
            {
                "镜号": scene.scene,
                "时长(秒)": scene.duration_seconds,
                "场景/地点": scene.location,
                "手机画面": scene.shot_type,
                "拍摄动作": scene.camera_movement,
                "画面内容": scene.description,
                "人物/产品动作": scene.subject_action,
                "口播/同期声": scene.narration,
                "字幕": scene.subtitle,
                "音乐/声音": scene.audio,
                "道具": scene.props,
                "执行注意": scene.execution_notes,
            }
            for scene in score_result.storyboard_guide
        ]
    )


def shooting_guide_dataframe(score_result):
    guide = score_result.shooting_guide
    if not guide:
        return pd.DataFrame([{"项目": "拍摄指导", "建议": "暂无"}])
    return pd.DataFrame(
        [
            {"项目": "光线与画面", "建议": guide.lighting},
            {"项目": "音乐与声音", "建议": guide.sound},
            {"项目": "人物状态与节奏", "建议": guide.performance},
            {"项目": "拍摄顺序", "建议": guide.schedule},
            {"项目": "场景规划", "建议": guide.location_plan},
            {"项目": "设备清单", "建议": guide.equipment},
            {"项目": "道具清单", "建议": guide.props},
            {"项目": "人员分工", "建议": guide.crew},
            {"项目": "封面标题", "建议": guide.cover_title},
            {"项目": "平台适配", "建议": guide.platform_notes},
            {"项目": "风险提醒", "建议": guide.risk_notes},
        ]
    )


def build_director_context(score_result) -> str:
    guide = score_result.shooting_guide
    context = {
        "original_script": st.session_state.get("last_original_script", ""),
        "composite": round(score_result.composite, 2),
        "scores": score_result.scores.to_dict(),
        "reasons": score_result.reasons,
        "storyboard_guide": [scene.model_dump() for scene in score_result.storyboard_guide],
        "shooting_guide": guide.model_dump() if guide else {},
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def render_director_chat(score_result, copywriter):
    context_text = build_director_context(score_result)
    context_id = hashlib.sha256(context_text.encode("utf-8")).hexdigest()
    if st.session_state.get("director_context_id") != context_id:
        st.session_state.director_context_id = context_id
        st.session_state.director_context = context_text
        st.session_state.director_chat_messages = [
            {
                "role": "assistant",
                "content": "我已读完当前评分结果、分镜脚本和拍摄指导。可以继续问我镜头调整、天气备选、连载策划、平台适配或现场执行问题。",
            }
        ]

    st.markdown('<p class="section-title">AI 导演智囊</p>', unsafe_allow_html=True)
    st.caption("基于上方评分、分镜和拍摄指导继续追问。")

    messages = st.session_state.get("director_chat_messages", [])
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "例如：第一镜如果遇到下雨天怎么改？接下来的视频该怎么策划连载？",
        key="director_chat_input",
    )
    if question:
        user_message = {"role": "user", "content": question}
        st.session_state.director_chat_messages.append(user_message)
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("AI 导演正在结合当前方案思考..."):
                try:
                    answer = copywriter.director_chat(
                        st.session_state.director_context,
                        st.session_state.director_chat_messages,
                        question,
                    )
                    st.markdown(answer)
                    st.session_state.director_chat_messages.append({"role": "assistant", "content": answer})
                except Exception as exc:
                    error_message = f"导演智囊回答失败：{type(exc).__name__}: {exc}"
                    st.error(error_message)
                    st.session_state.director_chat_messages.append({"role": "assistant", "content": error_message})


def render_score_results(score_result, copywriter):
    st.markdown('<p class="section-title">评分总览</p>', unsafe_allow_html=True)
    st.dataframe(score_dataframe(score_result), use_container_width=True, hide_index=True)
    st.metric("综合分", f"{score_result.composite:.2f}/10")

    if st.button("基于评分深度优化文案", type="primary", use_container_width=True):
        original = st.session_state.get("last_original_script", "")
        with st.spinner("正在基于扣分项重写文案..."):
            try:
                optimized = copywriter.optimize(original, score_result)
                st.session_state.optimized_script_result = optimized
            except Exception as exc:
                st.error(f"优化失败：{type(exc).__name__}: {exc}")
                with st.expander("查看底层错误详情", expanded=True):
                    st.exception(exc)

    optimized = st.session_state.get("optimized_script_result")
    if optimized is not None:
        st.markdown('<p class="section-title">原始文案 vs 优化后文案</p>', unsafe_allow_html=True)
        original_col, optimized_col = st.columns(2, gap="large")
        with original_col:
            st.text_area("原始文案", st.session_state.get("last_original_script", ""), height=320)
        with optimized_col:
            st.text_area("优化后文案", optimized.optimized_script, height=320)
        st.caption("优化重点：" + "；".join(optimized.key_changes + optimized.target_improvements))

    st.markdown('<p class="section-title">新手友好分镜指导</p>', unsafe_allow_html=True)
    st.dataframe(storyboard_dataframe(score_result), use_container_width=True, hide_index=True)

    st.markdown('<p class="section-title">手机拍摄执行指导</p>', unsafe_allow_html=True)
    st.dataframe(shooting_guide_dataframe(score_result), use_container_width=True, hide_index=True)
    render_director_chat(score_result, copywriter)


def build_evaluation_record(title: str, script_path: str, score_result) -> dict:
    return {
        "title": title,
        "script_path": script_path,
        "composite": round(score_result.composite, 2),
        "scores": score_result.scores.to_dict(),
        "storyboard_count": len(score_result.storyboard_guide),
        "created_at": datetime.now().isoformat(),
    }


def build_prediction_record(prediction, prediction_path: str) -> dict:
    return {
        "title": prediction.title,
        "prediction_path": prediction_path,
        "bucket": prediction.bucket,
        "center": prediction.center,
        "confidence": prediction.confidence,
        "composite": round(prediction.score_result.composite, 2),
        "created_at": datetime.now().isoformat(),
    }


def save_script(input_text: str) -> tuple:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_title = f"script_{timestamp}"
    script_path = os.path.join(settings.SCRIPTS_DIR, f"{script_title}.md")
    os.makedirs(settings.SCRIPTS_DIR, exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as file:
        file.write(f"# {script_title}\n\n{input_text}")
    return script_title, script_path


def save_uploaded_media(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return temp_file.name


def render_excel_download(path_value: str, label: str, key: str):
    if not path_value:
        return
    export_path = Path(path_value)
    if not export_path.exists():
        st.error(f"导出文件不存在：{export_path}")
        return
    try:
        buffer = BytesIO(export_path.read_bytes())
    except OSError as exc:
        st.error(f"读取导出文件失败：{type(exc).__name__}: {exc}")
        return
    st.download_button(
        label,
        data=buffer,
        file_name=export_path.name,
        mime=EXCEL_MIME,
        use_container_width=True,
        key=key,
    )


def evaluation_history_dataframe(records: list) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["创建时间", "脚本标题", "存储路径", "综合评分", "分镜数"])

    rows = []
    for item in records:
        rows.append(
            {
                "创建时间": item.get("created_at", ""),
                "脚本标题": item.get("title", ""),
                "存储路径": item.get("script_path", ""),
                "综合评分": item.get("composite", ""),
                "分镜数": item.get("storyboard_count", ""),
            }
        )
    return pd.DataFrame(rows)


def prediction_history_dataframe(records: list) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["创建时间", "脚本标题", "预测文件", "预测流量池", "中枢播放量(万)", "置信度", "综合评分"])

    rows = []
    for item in records:
        rows.append(
            {
                "创建时间": item.get("created_at", ""),
                "脚本标题": item.get("title", ""),
                "预测文件": item.get("prediction_path", ""),
                "预测流量池": item.get("bucket", ""),
                "中枢播放量(万)": item.get("center", ""),
                "置信度": item.get("confidence", ""),
                "综合评分": item.get("composite", ""),
            }
        )
    return pd.DataFrame(rows)


inject_style()
rubric_engine, _, predictor, copywriter, file_storage, json_storage, excel_exporter = init_clients()
state = json_storage.load_state()

with st.sidebar:
    st.markdown("### AI 灵感创作")
    product_info = st.text_area(
        "产品信息或创作意图",
        placeholder="例如：一款便携咖啡杯，卖点是保温、轻便、适合通勤；目标人群是上班族。",
        height=160,
    )
    if st.button("生成 3 个初始脚本", use_container_width=True):
        with st.spinner("正在生成 3 种风格脚本..."):
            try:
                st.session_state.script_ideas = copywriter.generate_ideas(product_info)
            except Exception as exc:
                st.error(f"灵感生成失败：{type(exc).__name__}: {exc}")
                with st.expander("查看底层错误详情"):
                    st.exception(exc)

    if "script_ideas" in st.session_state:
        for index, idea in enumerate(st.session_state.script_ideas.ideas, start=1):
            with st.expander(f"{index}. {idea.style}｜{idea.title}", expanded=index == 1):
                st.caption(idea.hook)
                st.text_area("脚本", idea.script, height=180, key=f"idea_script_{index}")
                if st.button("采用这个脚本", key=f"use_idea_{index}", use_container_width=True):
                    st.session_state.main_script_input = idea.script
                    st.session_state.pop("optimized_script_result", None)
                    st.rerun()

    st.divider()
    st.markdown("### 本地目录")
    st.caption(f"脚本：{settings.SCRIPTS_DIR}")
    st.caption(f"预测：{settings.PREDICTIONS_DIR}")
    st.caption(f"导出：{settings.EXPORTS_DIR}")
    st.divider()
    st.markdown("### 模型")
    st.caption(settings.MOONSHOT_MODEL)

render_header(state)

tab_breakdown, tab_plan, tab_predict, tab_history, tab_retro = st.tabs(
    ["爆款视频/音频拆解", "文案生产与评估", "播放预测", "历史资产", "数据校准"]
)

with tab_breakdown:
    st.markdown('<p class="section-title">上传视频/音频并转写</p>', unsafe_allow_html=True)
    st.caption("支持常见音频文件，也可尝试上传带清晰人声的视频文件。转写完成后会自动填入文案评估输入框。")
    uploaded_media = st.file_uploader(
        "选择要拆解的文件",
        type=["mp3", "wav", "m4a", "aac", "flac", "ogg", "opus", "mp4", "mov"],
        accept_multiple_files=False,
        key="breakdown_media_uploader",
    )

    if uploaded_media is not None:
        st.info(f"已选择：{uploaded_media.name}")
        if st.button("开始转写并填入文案评估", type="primary", use_container_width=True, key="transcribe_uploaded_media"):
            temp_path = None
            with st.spinner("正在调用阿里云 DashScope ASR 转写..."):
                try:
                    temp_path = save_uploaded_media(uploaded_media)
                    transcriber = create_transcriber(
                        settings.SPEECH_TO_TEXT_PROVIDER,
                        settings.DASHSCOPE_API_KEY,
                        settings.DASHSCOPE_ASR_MODEL,
                    )
                    transcript = transcriber.transcribe(temp_path)
                    st.session_state.asr_transcript = transcript
                    st.session_state.main_script_input = transcript
                    st.session_state.pop("optimized_script_result", None)
                    st.success("转写完成，文字已填入【文案生产与评估】输入框。")
                except Exception as exc:
                    st.error(f"转写失败：{type(exc).__name__}: {exc}")
                    with st.expander("查看 ASR 错误详情", expanded=True):
                        st.exception(exc)
                finally:
                    if temp_path:
                        try:
                            Path(temp_path).unlink(missing_ok=True)
                        except OSError:
                            pass

    if st.session_state.get("asr_transcript"):
        st.text_area("最近一次转写结果", st.session_state.asr_transcript, height=260)
        if st.button("再次填入文案评估", use_container_width=True, key="reuse_asr_transcript"):
            st.session_state.main_script_input = st.session_state.asr_transcript
            st.success("已重新填入【文案生产与评估】输入框。")

with tab_plan:
    left_col, right_col = st.columns([0.92, 1.55], gap="large")

    with left_col:
        st.markdown('<p class="section-title">输入文案</p>', unsafe_allow_html=True)
        input_text = st.text_area(
            "产品/品牌种草文案",
            placeholder="粘贴产品/品牌种草文案，或在左侧用 AI 灵感创作生成初稿...",
            height=420,
            key="main_script_input",
            label_visibility="collapsed",
        )
        run_eval = st.button("生成评估与拍摄方案", type="primary", use_container_width=True)

    with right_col:
        if run_eval:
            if not input_text.strip():
                st.error("请先输入文案内容。")
            else:
                with st.spinner("正在生成评分、分镜和手机拍摄方案..."):
                    try:
                        score_result = rubric_engine.score(input_text)
                        title, script_path = save_script(input_text)
                        json_storage.add_evaluation_record(build_evaluation_record(title, script_path, score_result))
                        st.session_state.last_score_result = score_result
                        st.session_state.last_original_script = input_text
                        st.session_state.last_script_title = title
                        st.session_state.last_script_path = script_path
                        st.session_state.pop("optimized_script_result", None)
                        st.success(f"已保存脚本：{script_path}")
                    except Exception as exc:
                        st.session_state.pop("last_score_result", None)
                        st.error(f"评估失败：{type(exc).__name__}: {exc}")
                        with st.expander("查看底层错误详情", expanded=True):
                            st.exception(exc)

        if "last_score_result" in st.session_state:
            render_score_results(st.session_state.last_score_result, copywriter)
            export_col, path_col = st.columns([0.4, 0.6])
            with export_col:
                if st.button("导出拍摄通告单 Excel", use_container_width=True, key="export_call_sheet_btn"):
                    try:
                        export_path = excel_exporter.export_call_sheet(
                            st.session_state.last_score_result,
                            st.session_state.get("last_script_title", "call_sheet"),
                        )
                        st.session_state.last_export_path = export_path
                    except Exception as exc:
                        st.error(f"导出拍摄通告单失败：{type(exc).__name__}: {exc}")
                        with st.expander("查看导出错误详情", expanded=True):
                            st.exception(exc)
            with path_col:
                if "last_export_path" in st.session_state:
                    export_path = Path(st.session_state.last_export_path)
                    st.success(f"已导出：{export_path}")
                    render_excel_download(st.session_state.last_export_path, "下载拍摄通告单", "download_call_sheet_btn")
        else:
            st.info("生成后将在这里看到评分、优化入口、分镜和手机拍摄指导。")

with tab_predict:
    scripts = file_storage.list_scripts()
    script_names = [item["name"] for item in scripts]
    if not script_names:
        st.warning("暂无脚本文件。")
    else:
        selected_script = st.selectbox("选择脚本", script_names)
        if st.button("生成播放量预测", type="primary", use_container_width=True):
            with st.spinner("正在评分、预测和生成反事实分析..."):
                try:
                    script_path = os.path.join(settings.SCRIPTS_DIR, selected_script)
                    script_content = Path(script_path).read_text(encoding="utf-8")
                    predictor.load_calibration_pool(json_storage.get_calibration_pool())
                    prediction = predictor.predict(script_content, selected_script.replace(".md", ""), script_path)
                    saved_path = file_storage.save_prediction(prediction)
                    json_storage.add_prediction_record(build_prediction_record(prediction, saved_path))
                    st.session_state.last_prediction = prediction
                    st.success(f"预测已保存：{saved_path}")
                except Exception as exc:
                    st.session_state.pop("last_prediction", None)
                    st.error(f"预测失败：{type(exc).__name__}: {exc}")
                    with st.expander("查看底层错误详情", expanded=True):
                        st.exception(exc)

    if "last_prediction" in st.session_state:
        prediction = st.session_state.last_prediction
        col1, col2, col3 = st.columns(3)
        col1.metric("预测流量池", prediction.bucket)
        col2.metric("中枢播放量", f"{prediction.center:.1f}万")
        col3.metric("置信度", prediction.confidence)
        st.dataframe(
            pd.DataFrame(
                [{"流量池": item.bucket, "概率": f"{int(item.probability * 100)}%"} for item in prediction.distribution]
            ),
            use_container_width=True,
            hide_index=True,
        )

with tab_history:
    state = json_storage.load_state()
    evaluations = state.get("evaluation_records", [])
    predictions = state.get("prediction_records", [])
    if st.button("导出历史记录 Excel", use_container_width=True, key="export_history_btn"):
        try:
            history_path = excel_exporter.export_history(evaluations, predictions)
            st.session_state.last_history_export_path = history_path
        except Exception as exc:
            st.error(f"导出历史记录失败：{type(exc).__name__}: {exc}")
            with st.expander("查看导出错误详情", expanded=True):
                st.exception(exc)
    if "last_history_export_path" in st.session_state:
        history_path = Path(st.session_state.last_history_export_path)
        st.success(f"已导出：{history_path}")
        render_excel_download(st.session_state.last_history_export_path, "下载历史记录", "download_history_btn")

    st.markdown('<p class="section-title">评估记录</p>', unsafe_allow_html=True)
    st.dataframe(evaluation_history_dataframe(evaluations), use_container_width=True, hide_index=True)

    st.markdown('<p class="section-title">预测记录</p>', unsafe_allow_html=True)
    st.dataframe(prediction_history_dataframe(predictions), use_container_width=True, hide_index=True)

with tab_retro:
    predictions = file_storage.list_predictions()
    prediction_names = [item["name"] for item in predictions]
    if not prediction_names:
        st.warning("暂无可复盘的预测文件。")
    else:
        with st.form("retro_calibration_form", clear_on_submit=False):
            selected_prediction = st.selectbox("选择预测文件", prediction_names)
            actual_plays = st.number_input("真实播放量（万）", min_value=0.0, step=0.1, format="%.1f")
            actual_likes = st.number_input("点赞数", min_value=0, step=1)
            actual_shares = st.number_input("分享数", min_value=0, step=1)
            submitted_retro = st.form_submit_button("提交复盘数据", type="primary", use_container_width=True)

        if submitted_retro:
            if actual_plays <= 0:
                st.error("请输入有效播放量。")
            else:
                try:
                    sample = {
                        "title": selected_prediction,
                        "actual_plays": actual_plays,
                        "actual_likes": actual_likes,
                        "actual_shares": actual_shares,
                        "timestamp": datetime.now().strftime("%Y-%m-%d"),
                    }
                    json_storage.add_calibration_sample(sample)
                    state = json_storage.load_state()
                    st.success(f"复盘数据已进入校准池，当前样本数：{state.get('calibration_samples', 0)}")
                except Exception as exc:
                    st.error(f"提交复盘数据失败：{type(exc).__name__}: {exc}")
                    with st.expander("查看复盘错误详情", expanded=True):
                        st.exception(exc)

    state = json_storage.load_state()
    st.metric("校准样本数", state.get("calibration_samples", 0))
