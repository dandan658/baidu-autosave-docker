// 版本管理配置
export const VERSION_CONFIG = {
  APP_VERSION: __APP_VERSION__,
  BUILD_TIME: __BUILD_TIME__,
  RELEASE_NOTES: '自动识别多季订阅、目录季数优先、支持重复集名分季整理',
  UPDATE_NOTES: {
    'v1.4.1': '修复多季订阅被命名为第一季；识别带剧名的中文、英文季目录；保留分享根目录季数',
    'v1.4.0': '统一玻璃视觉与交互动画；适配手机、平板和宽屏；修复导航数量标记错位',
    'v1.3.0': '移动文件后不重复转存；删除任务清除记忆；优化监控交互和后台并发；修复提取码和表单布局',
    'v1.2.0': '自定义任务名；合并或保留子目录；独立分季命名；修复正则捕获组重命名',
    'v1.1.5': '版本号改为从 package.json 自动注入',
    'v1.1.3': '前端重构版本 - Vue 3 + TypeScript',
    'v1.1.2': '优化轮询机制',
    'v1.1.1': '优化界面响应速度'
  }
} as const

export const APP_VERSION = VERSION_CONFIG.APP_VERSION
export const BUILD_TIME = VERSION_CONFIG.BUILD_TIME
export const RELEASE_NOTES = VERSION_CONFIG.RELEASE_NOTES
