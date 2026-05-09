from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapters.speech_to_text import create_transcriber
from config import settings
from core.analyzer import Analyzer
from core.bump_validator import BumpValidator
from core.predictor import Predictor
from core.rubric_engine import RubricEngine
from llm.deepseek_client import DeepSeekClient
from storage.excel_exporter import ExcelExporter
from storage.file_storage import FileStorage
from storage.supabase_storage import SupabaseStorage


console = Console()


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
    bump_validator = BumpValidator(llm_client)
    file_storage = FileStorage(settings.PREDICTIONS_DIR, settings.SCRIPTS_DIR)
    json_storage = SupabaseStorage(settings.STATE_FILE)
    return llm_client, rubric_engine, analyzer, predictor, bump_validator, file_storage, json_storage


@click.group()
def cli():
    pass


@cli.command()
@click.argument("script_path")
def score(script_path):
    _, rubric_engine, _, _, _, file_storage, _ = init_clients()

    try:
        script = file_storage.load_script(script_path)
        score_result = rubric_engine.score(script)

        score_table = Table(title="7维评分结果")
        score_table.add_column("维度", style="cyan")
        score_table.add_column("分数", style="magenta")
        score_table.add_column("理由", style="green")

        for dim, value in score_result.scores.to_dict().items():
            score_table.add_row(dim, str(value), score_result.reasons.get(dim, ""))

        console.print(score_table)
        console.print(f"\n[bold yellow]综合分[/bold yellow] {score_result.composite:.2f}/10")

        if score_result.storyboard_guide:
            console.print()
            console.print(Panel("[bold cyan]可执行分镜脚本[/bold cyan]", expand=False))
            storyboard_table = Table(show_header=True, header_style="bold magenta")
            storyboard_table.add_column("镜号", style="cyan", width=10)
            storyboard_table.add_column("秒", justify="right", width=5)
            storyboard_table.add_column("地点", style="yellow", width=14)
            storyboard_table.add_column("景别", width=10)
            storyboard_table.add_column("运镜", width=12)
            storyboard_table.add_column("画面/动作/字幕", style="white")
            storyboard_table.add_column("执行注意", style="green")

            for scene in score_result.storyboard_guide:
                storyboard_table.add_row(
                    scene.scene,
                    str(scene.duration_seconds),
                    scene.location,
                    scene.shot_type,
                    scene.camera_movement,
                    "\n".join(
                        item
                        for item in [
                            scene.description,
                            f"动作：{scene.subject_action}" if scene.subject_action else "",
                            f"旁白：{scene.narration}" if scene.narration else "",
                            f"字幕：{scene.subtitle}" if scene.subtitle else "",
                            f"声音：{scene.audio}" if scene.audio else "",
                            f"道具：{scene.props}" if scene.props else "",
                        ]
                        if item
                    ),
                    scene.execution_notes,
                )

            console.print(storyboard_table)

        if score_result.shooting_guide:
            console.print()
            console.print(Panel("[bold cyan]拍摄执行指导[/bold cyan]", expand=False))
            guide = score_result.shooting_guide
            guide_table = Table(show_header=True, header_style="bold magenta")
            guide_table.add_column("项目", style="cyan", width=14)
            guide_table.add_column("建议", style="white")
            for label, value in [
                ("光线与色彩", guide.lighting),
                ("声音与BGM", guide.sound),
                ("出镜与表演", guide.performance),
                ("拍摄顺序", guide.schedule),
                ("取景点规划", guide.location_plan),
                ("设备清单", guide.equipment),
                ("道具清单", guide.props),
                ("人员分工", guide.crew),
                ("封面标题", guide.cover_title),
                ("平台适配", guide.platform_notes),
                ("风险提醒", guide.risk_notes),
            ]:
                guide_table.add_row(label, value or "暂无建议")
            console.print(guide_table)

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command()
@click.argument("script_path")
def predict(script_path):
    _, _, _, predictor, _, file_storage, json_storage = init_clients()

    try:
        script = file_storage.load_script(script_path)
        title = Path(script_path).stem
        state = json_storage.load_state()
        predictor.load_calibration_pool(state.get("calibration_pool", []))
        prediction = predictor.predict(script, title, script_path)
        saved_path = file_storage.save_prediction(prediction)

        console.print(f"[bold green]预测已保存：[/bold green] {saved_path}")
        table = Table(title="预测概览")
        table.add_column("项目", style="cyan")
        table.add_column("值", style="magenta")
        table.add_row("Bucket", prediction.bucket)
        table.add_row("中枢", f"{prediction.center:.1f}w")
        table.add_row("综合分", f"{prediction.score_result.composite:.2f}")
        table.add_row("置信度", prediction.confidence)
        console.print(table)

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command()
@click.argument("prediction_path")
def retro(prediction_path):
    _, _, _, _, _, _, json_storage = init_clients()

    try:
        console.print(f"[bold blue]正在复盘：[/bold blue] {prediction_path}")
        plays = float(click.prompt("播放量（万）"))
        likes = float(click.prompt("点赞数"))
        shares = float(click.prompt("分享数"))
        published_at = click.prompt("发布日期（YYYY-MM-DD）")

        sample = {
            "title": Path(prediction_path).name,
            "actual_plays": plays,
            "actual_likes": likes,
            "actual_shares": shares,
            "timestamp": published_at,
        }

        json_storage.add_calibration_sample(sample)
        console.print("[bold green]复盘数据已保存。[/bold green]")

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command()
@click.option("--propose", required=True, help='升级建议，例如 "ER*2.0, add VR"')
def bump(propose):
    _, rubric_engine, _, _, bump_validator, _, json_storage = init_clients()

    try:
        current_rubric = rubric_engine.rubric
        new_rubric = bump_validator.propose_bump(current_rubric, propose)
        if not new_rubric:
            console.print("[red]无效的升级提议。[/red]")
            return

        state = json_storage.load_state()
        calibration_pool = state.get("calibration_pool", [])
        if len(calibration_pool) < 3:
            console.print("[yellow]警告：校准池样本不足，建议至少3个样本后再验证。[/yellow]")

        validation = bump_validator.validate(current_rubric, new_rubric, calibration_pool)
        console.print(f"[bold blue]排序一致性：[/bold blue] {validation.consistency:.2%}")
        console.print(f"[bold blue]Pairwise回归：[/bold blue] {'存在' if validation.pairwise_regression else '无'}")
        console.print(f"[bold blue]跨模型审计：[/bold blue] {'通过' if validation.audit_passed else '拒绝'}")

        if validation.audit_reason:
            console.print(f"[bold blue]审计理由：[/bold blue] {validation.audit_reason}")

        if validation.passed:
            json_storage.update_state({"rubric_version": new_rubric.current_version})
            console.print("[bold green]升级验证通过。[/bold green]")
        else:
            console.print("[bold red]升级验证失败。[/bold red]")

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command()
@click.argument("audio_file")
def transcribe(audio_file):
    try:
        transcriber = create_transcriber(
            settings.SPEECH_TO_TEXT_PROVIDER,
            settings.DASHSCOPE_API_KEY,
            settings.WHISPER_MODEL,
        )
        text = transcriber.transcribe(audio_file)
        console.print("[bold green]转录完成。[/bold green]")
        console.print(f"[yellow]文本内容：[/yellow]\n{text}")

        script_path = Path("scripts") / f"{Path(audio_file).stem}.md"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as file:
            file.write(f"# {Path(audio_file).name}\n\n{text}")
        console.print(f"[bold blue]已保存到：[/bold blue] {script_path}")

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command()
def status():
    _, _, _, _, _, file_storage, json_storage = init_clients()

    try:
        state = json_storage.load_state()
        predictions = file_storage.list_predictions()
        scripts = file_storage.list_scripts()

        table = Table(title="项目状态")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="magenta")
        table.add_row("当前Rubric版本", state.get("rubric_version", "未知"))
        table.add_row("校准样本数", str(state.get("calibration_samples", 0)))
        table.add_row("预测文件数", str(len(predictions)))
        table.add_row("脚本文件数", str(len(scripts)))
        baseline_plays = state.get("baseline_plays")
        table.add_row("基准播放量", f"{baseline_plays}w" if baseline_plays is not None else "未设置")
        console.print(table)

        if predictions:
            console.print("\n[bold blue]最近预测：[/bold blue]")
            for item in predictions[:3]:
                console.print(f"  - {item['name']}")

    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command("export-call-sheet")
@click.argument("script_path")
def export_call_sheet(script_path):
    _, rubric_engine, _, _, _, file_storage, _ = init_clients()

    try:
        script = file_storage.load_script(script_path)
        score_result = rubric_engine.score(script)
        exporter = ExcelExporter(settings.EXPORTS_DIR)
        export_path = exporter.export_call_sheet(score_result, Path(script_path).stem)
        console.print(f"[bold green]拍摄通告单已导出：[/bold green] {export_path}")
    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


@cli.command("export-history")
def export_history():
    _, _, _, _, _, _, json_storage = init_clients()

    try:
        exporter = ExcelExporter(settings.EXPORTS_DIR)
        export_path = exporter.export_history(
            json_storage.list_evaluation_records(),
            json_storage.list_prediction_records(),
        )
        console.print(f"[bold green]历史记录已导出：[/bold green] {export_path}")
    except Exception as exc:
        console.print(f"[red]错误：[/red] {exc}")


if __name__ == "__main__":
    cli()
