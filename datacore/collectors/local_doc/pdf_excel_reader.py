"""PDF/Excel 读取骨架。

提供本地 PDF 和 Excel 文件读取能力。
依赖为可选，不可用时返回空结果。
"""

from __future__ import annotations

import os
from typing import Any


class PdfExcelReader:
    """PDF/Excel 文件读取器。

    支持读取本地 PDF 和 Excel 文件内容。
    外部依赖（pdfplumber / openpyxl）为可选。

    Attributes:
        name: 读取器名称。
        description: 读取器描述。
    """

    name: str = "pdf_excel_reader"
    description: str = "本地 PDF/Excel 文件内容读取器"

    def __init__(self) -> None:
        """初始化文件读取器。"""
        pass

    def check_available(self) -> bool:
        """检查读取器是否可用。

        只要能读取 Excel（pandas 内置）就算可用。

        Returns:
            True 表示可用。
        """
        try:
            import pandas as pd  # noqa: F401
            return True
        except ImportError:
            return False

    def _check_pdf_available(self) -> bool:
        """检查 PDF 读取是否可用。"""
        try:
            import pdfplumber  # noqa: F401
            return True
        except ImportError:
            try:
                import PyPDF2  # noqa: F401
                return True
            except ImportError:
                return False

    def fetch(self, file_path: str, **kwargs: Any) -> dict[str, Any]:
        """读取文件内容。

        根据文件扩展名自动选择读取方式。

        Args:
            file_path: 文件路径。
            **kwargs: 额外参数。

        Returns:
            读取结果字典，包含：
            - success: 是否成功
            - file_path: 文件路径
            - file_type: 文件类型
            - data: 读取的数据
            - error: 错误信息（失败时）
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "file_path": file_path,
                "file_type": None,
                "data": None,
                "error": f"文件不存在: {file_path}",
            }

        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".xlsx", ".xls", ".csv"):
            return self._read_excel(file_path, **kwargs)
        elif ext == ".pdf":
            return self._read_pdf(file_path, **kwargs)
        else:
            return {
                "success": False,
                "file_path": file_path,
                "file_type": ext,
                "data": None,
                "error": f"不支持的文件类型: {ext}",
            }

    def _read_excel(self, file_path: str, sheet_name: str | int = 0,
                    **kwargs: Any) -> dict[str, Any]:
        """读取 Excel/CSV 文件。

        Args:
            file_path: 文件路径。
            sheet_name: 工作表名或索引。
            **kwargs: 额外参数。

        Returns:
            读取结果。
        """
        try:
            import pandas as pd

            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path, **kwargs)
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

            return {
                "success": True,
                "file_path": file_path,
                "file_type": "excel",
                "sheet_name": sheet_name,
                "data": df.to_dict("records"),
                "row_count": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "file_type": "excel",
                "data": None,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _read_pdf(self, file_path: str, **kwargs: Any) -> dict[str, Any]:
        """读取 PDF 文件。

        Args:
            file_path: 文件路径。
            **kwargs: 额外参数。

        Returns:
            读取结果。
        """
        if not self._check_pdf_available():
            return {
                "success": False,
                "file_path": file_path,
                "file_type": "pdf",
                "data": None,
                "error": "PDF 读取库未安装，请先 pip install pdfplumber",
            }

        try:
            import pdfplumber

            pages_text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)

            return {
                "success": True,
                "file_path": file_path,
                "file_type": "pdf",
                "page_count": len(pages_text),
                "data": "\n".join(pages_text),
                "pages": pages_text,
            }
        except ImportError:
            try:
                import PyPDF2

                pages_text = []
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text = page.extract_text() or ""
                        pages_text.append(text)

                return {
                    "success": True,
                    "file_path": file_path,
                    "file_type": "pdf",
                    "page_count": len(pages_text),
                    "data": "\n".join(pages_text),
                    "pages": pages_text,
                }
            except Exception as e:
                return {
                    "success": False,
                    "file_path": file_path,
                    "file_type": "pdf",
                    "data": None,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "file_type": "pdf",
                "data": None,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def list_sheets(self, file_path: str) -> dict[str, Any]:
        """列出 Excel 文件的所有工作表。

        Args:
            file_path: Excel 文件路径。

        Returns:
            工作表列表结果。
        """
        try:
            import pandas as pd

            xl = pd.ExcelFile(file_path)
            return {
                "success": True,
                "file_path": file_path,
                "sheets": xl.sheet_names,
                "sheet_count": len(xl.sheet_names),
            }
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "sheets": [],
                "error": str(e),
            }
