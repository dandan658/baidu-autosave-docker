"""Pure naming rules shared by task validation and the transfer planner."""
import posixpath
import re

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.ts', '.m2ts', '.wmv', '.flv', '.webm'}
SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.ssa', '.vtt', '.sub'}


def safe_name(value):
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', value).strip(' .')
    if not value or value in ('.', '..'):
        raise ValueError('文件名称不能为空或包含路径跳转')
    return value


def replacement(value):
    # Accept both the UI's $1 notation and Python's \1 / \g<1> notation.
    return re.sub(r'\$(\d+)', lambda m: '\\g<' + m[1] + '>', value)


def task_options(data, previous=None):
    previous = previous or {}
    result = {key: data.get(key, previous.get(key, default)) for key, default in (
        ('media_type', 'other'), ('flatten', False), ('auto_rename', False), ('season', 1), ('season_folders', []))}
    if result['media_type'] not in ('other', 'movie', 'tv'):
        raise ValueError('资源类型必须为普通文件、电影或电视剧')
    for key in ('flatten', 'auto_rename'):
        if not isinstance(result[key], bool):
            raise ValueError(f'{key} 必须为布尔值')
    if isinstance(result['season'], bool) or not isinstance(result['season'], int) or not 1 <= result['season'] <= 999:
        raise ValueError('季数必须是 1 至 999 的整数')
    if result['auto_rename']:
        if result['media_type'] == 'other' or not data.get('name', previous.get('name', '')).strip():
            raise ValueError('自动命名需要选择电影或电视剧并填写自定义任务名称')
    if not isinstance(result['season_folders'], list) or len(result['season_folders']) > 100:
        raise ValueError('分季目录规则必须为列表，最多 100 条')
    rules, seen = [], set()
    for rule in result['season_folders']:
        if not isinstance(rule, dict):
            raise ValueError('分季目录规则格式不正确')
        source = str(rule.get('source', '')).strip().strip('/')
        season = rule.get('season', 1)
        if not source or '\\' in source or any(p in ('', '.', '..') for p in source.split('/')) or source in seen:
            raise ValueError('源子目录必须填写不重复的相对路径，不能包含路径跳转')
        if isinstance(season, bool) or not isinstance(season, int) or not 1 <= season <= 999:
            raise ValueError('每个子目录的季数必须为 1 至 999 的整数')
        name = str(rule.get('name', '')).strip() or f'Season {season:02d}'
        if safe_name(name) != name:
            raise ValueError('新季目录名不能包含斜杠、特殊字符或路径跳转')
        rules.append({'source': source, 'season': season, 'name': name})
        seen.add(source)
    result['season_folders'] = rules
    if rules and result['media_type'] != 'tv':
        raise ValueError('分季目录规则只适用于电视剧')
    pattern = data.get('regex_pattern', previous.get('regex_pattern', '')) or ''
    replace = data.get('regex_replace', previous.get('regex_replace', '')) or ''
    if pattern:
        compiled = re.compile(pattern)
        if replace:
            compiled.sub(replacement(replace), '')
    return result


def regex_filename(path, task):
    parent, filename = posixpath.split(path)
    pattern, replace = task.get('regex_pattern', ''), task.get('regex_replace', '')
    if pattern and not re.search(pattern, filename):
        return False, path
    if replace:
        renamed = re.sub(pattern, replacement(replace), filename) if pattern else replace
        # Literal names without an extension retain the original extension.
        if not posixpath.splitext(renamed)[1]:
            renamed += posixpath.splitext(filename)[1]
        if '/' in renamed or '\\' in renamed or renamed in ('', '.', '..'):
            raise ValueError('重命名结果必须是文件名，不能包含目录')
        return True, posixpath.join(parent, safe_name(renamed))
    return True, path


def episode(path, default_season=1):
    stem = posixpath.splitext(posixpath.basename(path))[0]
    match = re.search(r'(?i)(?<![a-z0-9])S(\d{1,3})[ ._-]*E(\d{1,4})(?!\d)', stem)
    if match:
        return int(match[1]), int(match[2])
    parent_season = re.search(r'(?i)(?:^|/)(?:season[ ._-]*|S)(\d{1,3})(?:/|$)', posixpath.dirname(path))
    season = int(parent_season[1]) if parent_season else default_season
    for pattern in (r'第\s*(\d{1,4})\s*[集话話]', r'(?i)(?<![a-z0-9])(?:EP?|episode)[ ._-]*(\d{1,4})(?!\d)', r'^\s*(\d{1,4})(?=$|[ ._\-])'):
        match = re.search(pattern, stem)
        if match:
            number = int(match[1])
            if number in (360, 480, 576, 720, 1080, 2160, 4320) or 1900 <= number <= 2099:
                continue
            return season, number
    return None


def destination_name(path, task):
    """Return (included, relative destination, warning). No network side effects."""
    included, renamed = regex_filename(path, task)
    if not included:
        return False, path, ''
    season = task.get('season', 1)
    mapped_parent = posixpath.dirname(path)
    matched_rule = None
    for rule in sorted(task.get('season_folders', []), key=lambda r: len(r['source']), reverse=True):
        prefix = rule['source'].strip('/')
        if path.startswith(prefix + '/'):
            season = rule['season']
            mapped_parent = posixpath.dirname(posixpath.join(rule.get('name') or f'Season {season:02d}', path[len(prefix) + 1:]))
            matched_rule = rule
            break
    if task.get('media_type') == 'tv' and not matched_rule:
        for part in posixpath.dirname(path).split('/'):
            match = re.fullmatch(r'(?i)(?:season[ ._-]*|s)(\d{1,3})', part) or re.fullmatch(r'第?(\d{1,3})季', part)
            chinese = re.fullmatch(r'第?([一二三四五六七八九十])季', part)
            if match or chinese:
                season = int(match[1]) if match else '一二三四五六七八九十'.index(chinese[1]) + 1
                parts = mapped_parent.split('/')
                parts[parts.index(part)] = f'Season {season:02d}'
                mapped_parent = '/'.join(parts)
                break
    renamed = posixpath.join(mapped_parent, posixpath.basename(renamed))
    if task.get('auto_rename'):
        ext = posixpath.splitext(path)[1].lower()
        if ext not in VIDEO_EXTENSIONS | SUBTITLE_EXTENSIONS:
            return False, path, ''
        title = safe_name(task['name'])
        if task['media_type'] == 'tv':
            parsed = episode(path, season)
            if parsed is None:
                return False, path, f'无法识别集数，跳过并保留源文件：{path}'
            detected_season, number = parsed
            # An explicit per-directory rule takes precedence over filename tags.
            season = season if matched_rule else detected_season
            filename = f'{title} - S{season:02d}E{number:02d}'
        else:
            filename = title
        # Preserve subtitle language / forced markers so sidecars stay distinct.
        if ext in SUBTITLE_EXTENSIONS:
            suffix = re.search(r'(?i)[. _-](zh-cn|zh-tw|chs|cht|zh|en|eng|forced|简体|繁体|双语)$', posixpath.splitext(path)[0])
            if suffix:
                filename += '.' + suffix[1].lower()
        if not mapped_parent and task['media_type'] == 'tv' and not task.get('flatten'):
            mapped_parent = f'Season {season:02d}'
        renamed = posixpath.join(mapped_parent, filename + ext)
    return True, posixpath.basename(renamed) if task.get('flatten') else renamed, ''
