from __future__ import annotations

import numpy as np
from markdown_it import MarkdownIt


class SectionAnalyzer:
    def __init__(self):
        self.md = MarkdownIt()

    @staticmethod
    def expected_columns() -> list[str]:
        columns = ["repository_owner", "repository_name", "file_url"]
        for level in range(1, 7):
            columns.append(f"total_h{level}")
        for parent_level in range(1, 6):
            for child_level in range(parent_level + 1, 7):
                columns.append(f"median_h{child_level}_under_h{parent_level}")
        for level in range(1, 7):
            columns.extend([f"avg_loc_h{level}", f"median_loc_h{level}"])
        return columns

    def analyze(self, markdown_content: str) -> dict:
        """Analyze markdown content and return structural metrics.

        Metrics returned are consistent with the previous script:
        - total_h1..total_h6
        - median_h{child}_under_h{parent}
        - avg_loc_h{n}, median_loc_h{n} for n in 1..6
        """
        tokens = self.md.parse(markdown_content)
        lines = markdown_content.splitlines()
        num_lines = len(lines)

        headers = []
        for i, token in enumerate(tokens):
            if token.type == 'heading_open':
                level = int(token.tag[1])
                header_name = tokens[i + 1].content.strip() if (i + 1) < len(tokens) else ""
                start_line = token.map[0] if token.map else 0
                headers.append({'level': level, 'name': header_name, 'start_line': start_line})

        if not headers:
            return {}

        loc_per_header_level = {i: [] for i in range(1, 7)}
        for i, header in enumerate(headers):
            start_line = header['start_line']
            end_line = num_lines
            for j in range(i + 1, len(headers)):
                next_header = headers[j]
                if next_header['level'] <= header['level']:
                    end_line = next_header['start_line']
                    break

            section_lines = lines[start_line + 1: end_line]
            loc_count = 0
            in_code_block = False
            for line in section_lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block and line.strip():
                    loc_count += 1

            header['loc'] = loc_count
            loc_per_header_level[header['level']].append(loc_count)

        metrics = {}
        for level in range(1, 7):
            metrics[f'total_h{level}'] = sum(1 for h in headers if h['level'] == level)

        for p_level in range(1, 6):
            for c_level in range(p_level + 1, 7):
                key = f"median_h{c_level}_under_h{p_level}"
                counts_for_median = []
                for i, p_header in enumerate(headers):
                    if p_header['level'] == p_level:
                        child_count = 0
                        for j in range(i + 1, len(headers)):
                            next_header = headers[j]
                            if next_header['level'] <= p_level:
                                break
                            if next_header['level'] == c_level:
                                child_count += 1
                        counts_for_median.append(child_count)
                metrics[key] = float(np.median(counts_for_median)) if counts_for_median else 0.0

        for level in range(1, 7):
            counts = loc_per_header_level.get(level, [])
            metrics[f'avg_loc_h{level}'] = float(np.mean(counts)) if counts else 0.0
            metrics[f'median_loc_h{level}'] = float(np.median(counts)) if counts else 0.0

        return metrics
