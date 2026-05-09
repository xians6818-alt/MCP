from datetime import datetime
from pathlib import Path
from typing import Iterable, List
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from models.score import ScoreResult


class ExcelExporter:
    def __init__(self, exports_dir: str = "./exports"):
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_call_sheet(self, score_result: ScoreResult, title: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self._safe_filename(title or "call_sheet")
        path = self.exports_dir / f"{timestamp}_{safe_title}_call_sheet.xlsx"

        sheets = [
            ("评分总览", self._score_rows(score_result)),
            ("可执行分镜", self._storyboard_rows(score_result)),
            ("拍摄指导", self._shooting_guide_rows(score_result)),
        ]
        self._write_xlsx(path, sheets)
        return str(path)

    def export_history(self, evaluations: list, predictions: list) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.exports_dir / f"{timestamp}_history.xlsx"
        sheets = [
            ("评估记录", self._evaluation_rows(evaluations)),
            ("预测记录", self._prediction_rows(predictions)),
        ]
        self._write_xlsx(path, sheets)
        return str(path)

    def _score_rows(self, score_result: ScoreResult) -> List[List[object]]:
        rows = [["维度", "分数", "评分理由"]]
        for dim, value in score_result.scores.to_dict().items():
            rows.append([dim, value, score_result.reasons.get(dim, "")])
        rows.append([])
        rows.append(["综合分", round(score_result.composite, 2), "满分10分"])
        return rows

    def _storyboard_rows(self, score_result: ScoreResult) -> List[List[object]]:
        rows = [
            [
                "镜号",
                "时长(秒)",
                "地点",
                "景别",
                "运镜",
                "画面",
                "人物/主体动作",
                "旁白/同期声",
                "字幕",
                "声音",
                "道具",
                "执行注意",
            ]
        ]
        for scene in score_result.storyboard_guide:
            rows.append(
                [
                    scene.scene,
                    scene.duration_seconds,
                    scene.location,
                    scene.shot_type,
                    scene.camera_movement,
                    scene.description,
                    scene.subject_action,
                    scene.narration,
                    scene.subtitle,
                    scene.audio,
                    scene.props,
                    scene.execution_notes,
                ]
            )
        return rows

    def _shooting_guide_rows(self, score_result: ScoreResult) -> List[List[object]]:
        guide = score_result.shooting_guide
        rows = [["项目", "建议"]]
        if not guide:
            rows.append(["拍摄指导", "暂无"])
            return rows

        rows.extend(
            [
                ["光线与色彩", guide.lighting],
                ["声音与BGM", guide.sound],
                ["出镜与表演", guide.performance],
                ["拍摄顺序", guide.schedule],
                ["取景点规划", guide.location_plan],
                ["设备清单", guide.equipment],
                ["道具清单", guide.props],
                ["人员分工", guide.crew],
                ["封面标题", guide.cover_title],
                ["平台适配", guide.platform_notes],
                ["风险提醒", guide.risk_notes],
            ]
        )
        return rows

    def _evaluation_rows(self, evaluations: list) -> List[List[object]]:
        rows = [["创建时间", "标题", "脚本路径", "综合分", "ER", "SR", "HP", "QL", "NA", "AB", "SAT"]]
        for item in evaluations:
            scores = item.get("scores", {})
            rows.append(
                [
                    item.get("created_at", ""),
                    item.get("title", ""),
                    item.get("script_path", ""),
                    item.get("composite", ""),
                    scores.get("ER", ""),
                    scores.get("SR", ""),
                    scores.get("HP", ""),
                    scores.get("QL", ""),
                    scores.get("NA", ""),
                    scores.get("AB", ""),
                    scores.get("SAT", ""),
                ]
            )
        return rows

    def _prediction_rows(self, predictions: list) -> List[List[object]]:
        rows = [["创建时间", "标题", "预测文件", "Bucket", "中枢播放量(万)", "置信度", "综合分"]]
        for item in predictions:
            rows.append(
                [
                    item.get("created_at", ""),
                    item.get("title", ""),
                    item.get("prediction_path", ""),
                    item.get("bucket", ""),
                    item.get("center", ""),
                    item.get("confidence", ""),
                    item.get("composite", ""),
                ]
            )
        return rows

    def _write_xlsx(self, path: Path, sheets: List[tuple]):
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types(len(sheets)))
            archive.writestr("_rels/.rels", self._root_rels())
            archive.writestr("xl/workbook.xml", self._workbook_xml(sheets))
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels(len(sheets)))
            archive.writestr("xl/styles.xml", self._styles_xml())
            for index, (_, rows) in enumerate(sheets, start=1):
                archive.writestr(f"xl/worksheets/sheet{index}.xml", self._sheet_xml(rows))

    def _sheet_xml(self, rows: Iterable[Iterable[object]]) -> str:
        row_xml = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                ref = f"{self._column_name(col_index)}{row_index}"
                cells.append(self._cell_xml(ref, value))
            row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            + "".join(row_xml)
            + "</sheetData></worksheet>"
        )

    def _cell_xml(self, ref: str, value: object) -> str:
        if value is None:
            value = ""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        text = escape(str(value), {'"': "&quot;"})
        return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    def _content_types(self, sheet_count: int) -> str:
        sheet_overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            f"{sheet_overrides}</Types>"
        )

    def _root_rels(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>'
        )

    def _workbook_xml(self, sheets: List[tuple]) -> str:
        sheet_xml = "".join(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheet_xml}</sheets></workbook>"
        )

    def _workbook_rels(self, sheet_count: int) -> str:
        rels = "".join(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, sheet_count + 1)
        )
        rels += (
            f'<Relationship Id="rId{sheet_count + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{rels}</Relationships>"
        )

    def _styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<fonts count=\"1\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts>"
            "<fills count=\"1\"><fill><patternFill patternType=\"none\"/></fill></fills>"
            "<borders count=\"1\"><border/></borders>"
            "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
            "<cellXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/></cellXfs>"
            "</styleSheet>"
        )

    def _column_name(self, index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _safe_filename(self, value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in "-_" else "_" for char in value.strip())
        return cleaned[:40] or "export"
