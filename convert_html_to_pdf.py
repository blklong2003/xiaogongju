"""
批量将 HTML 文件转换为 PDF（基于 Playwright）
"""
import argparse
import logging
import sys
from pathlib import Path

from playwright.sync_api import PdfMargins, sync_playwright

# ── 默认配置 ──────────────────────────────────────────
DEFAULT_INPUT   = r'D:\OneDrive\gt2016帮助文档\GT-ISE帮助文档'
DEFAULT_OUTPUT  = r'D:\OneDrive\gt2016帮助文档\PDF'
DEFAULT_FORMAT  = 'A4'
DEFAULT_MARGIN: PdfMargins = {
    'top': '10mm', 'bottom': '10mm',
    'left': '10mm', 'right': '10mm',
}
# ──────────────────────────────────────────────────────


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger('html2pdf')
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def convert_all(
    input_dir: Path,
    output_dir: Path,
    page_format: str,
    margin: PdfMargins,
    print_background: bool,
    no_sandbox: bool,
    logger: logging.Logger,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(input_dir.rglob('*.htm*')) + list(input_dir.rglob('*.html'))
    if not html_files:
        logger.error('未找到 HTML 文件，请检查 INPUT_DIR 路径')
        sys.exit(1)

    logger.info('找到 %d 个 HTML 文件，开始转换...', len(html_files))

    launch_args = []
    if no_sandbox:
        launch_args.append('--no-sandbox')

    total = len(html_files)
    success = 0
    fail = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(args=launch_args)
        context = browser.new_context()

        for idx, html_file in enumerate(html_files, 1):
            # 保留子目录结构
            rel_path = html_file.relative_to(input_dir)
            pdf_path = output_dir / rel_path.with_suffix('.pdf')
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            file_uri = html_file.resolve().as_uri()
            try:
                page = context.new_page()
                page.goto(file_uri, wait_until='networkidle')
                page.pdf(
                    path=str(pdf_path),
                    format=page_format,
                    margin=margin,
                    print_background=print_background,
                )
                page.close()
                logger.info('[%d/%d]  ✓  %s', idx, total, html_file.name)
                success += 1
            except Exception as e:
                logger.warning('[%d/%d]  ✗  %s  —  %s', idx, total, html_file.name, e)
                fail += 1

        context.close()
        browser.close()

    logger.info(
        '转换完成！成功 %d，失败 %d，PDF 保存至 %s',
        success, fail, output_dir
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='HTML → PDF 批量转换工具')

    parser.add_argument('-i', '--input', default=DEFAULT_INPUT,
                        help=f'HTML 目录（默认: {DEFAULT_INPUT}）')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT,
                        help=f'PDF 输出目录（默认: {DEFAULT_OUTPUT}）')
    parser.add_argument('--format', default=DEFAULT_FORMAT,
                        choices=['A4', 'A3', 'Letter'],
                        help=f'纸张大小（默认: {DEFAULT_FORMAT}）')
    parser.add_argument('--margin-top', default='10mm')
    parser.add_argument('--margin-bottom', default='10mm')
    parser.add_argument('--margin-left', default='10mm')
    parser.add_argument('--margin-right', default='10mm')
    parser.add_argument('--no-background', action='store_false', dest='print_background',
                        help='不打印背景色/图片')
    parser.add_argument('--no-sandbox', action='store_true',
                        help='添加 --no-sandbox 参数启动 Chromium')
    parser.add_argument('--log-file', default=None,
                        help='日志文件路径（默认: OUTPUT_DIR/convert.log）')
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_dir.is_dir():
        print(f'错误: 输入目录不存在 → {input_dir}')
        sys.exit(1)

    log_file = Path(args.log_file) if args.log_file else output_dir / 'convert.log'
    logger = setup_logger(log_file)

    margin: PdfMargins = {
        'top': args.margin_top,
        'bottom': args.margin_bottom,
        'left': args.margin_left,
        'right': args.margin_right,
    }

    logger.info('=' * 50)
    logger.info('输入目录: %s', input_dir)
    logger.info('输出目录: %s', output_dir)
    logger.info('纸张格式: %s', args.format)
    logger.info('边距: %s', margin)
    logger.info('打印背景: %s', args.print_background)
    logger.info('日志文件: %s', log_file)
    logger.info('=' * 50)

    convert_all(
        input_dir=input_dir,
        output_dir=output_dir,
        page_format=args.format,
        margin=margin,
        print_background=args.print_background,
        no_sandbox=args.no_sandbox,
        logger=logger,
    )


if __name__ == '__main__':
    main()
