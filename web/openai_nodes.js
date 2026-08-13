import { app } from "../../../scripts/app.js";

const EDITABLE_TEXT = "OpenAITextEditor";

// ---------- Editable Text ----------

// 将输入文本显示到编辑框；输入未变化时保留用户编辑，输入变化时跟随新输入。
// followInput=false 用于缓存恢复（页面刷新等）：此时输入并未真正变化，保留用户编辑
function updateEditableText(node, message, followInput = true) {
  const raw = message?.text;
  if (raw === undefined) return;
  const text = Array.isArray(raw) ? raw[0] : raw;
  if (text === undefined || text === node.lastShownText) return;
  if (!followInput) {
    const userWidget = node.widgets?.find((w) => w.name === "text_user");
    if (userWidget?.value) return; // 缓存恢复时保留用户编辑
  }
  const widget = node.widgets?.find((w) => w.name === "text");
  if (!widget) return;
  widget.value = text;
  node.lastShownText = text;
  // 输入变化：放弃针对旧输入的编辑标记，编辑框跟随新输入
  const userWidget = node.widgets?.find((w) => w.name === "text_user");
  const baseWidget = node.widgets?.find((w) => w.name === "text_base");
  if (userWidget) userWidget.value = "";
  if (baseWidget) baseWidget.value = "";
}

function setupEditableText(node) {
  const textWidget = node.widgets?.find((w) => w.name === "text");
  const userWidget = node.widgets?.find((w) => w.name === "text_user");
  const baseWidget = node.widgets?.find((w) => w.name === "text_base");
  if (!textWidget || !userWidget || !baseWidget) return;
  if (!node._textUserSetup) {
    node._textUserSetup = true;
    // text_user / text_base 为隐藏的内部输入：不绘制、不占布局，值仍随 prompt 提交
    // DOM widget 渲染器读取顶层 hidden 标志（options.hidden 仅为兼容旧版）
    for (const w of [userWidget, baseWidget]) {
      w.hidden = true;
      Object.assign(w.options || (w.options = {}), { hidden: true });
    }
    // 用户编辑编辑框时同步 text_user（编辑内容）与 text_base（编辑时的输入）
    const onTextChanged = textWidget.callback;
    textWidget.callback = function (value, ...args) {
      userWidget.value = value;
      baseWidget.value = node.lastShownText ?? "";
      if (onTextChanged) onTextChanged.call(this, value, ...args);
    };
    // 兜底：提交/保存时确保 text_user 与编辑框一致（多行文本框失焦才触发 callback）
    const serializeWidgets = node.serializeWidgets?.bind(node);
    node.serializeWidgets = function () {
      if (userWidget.value !== textWidget.value) {
        userWidget.value = textWidget.value;
        baseWidget.value = node.lastShownText ?? "";
      }
      return serializeWidgets ? serializeWidgets() : this.widgets.map((w) => w.value);
    };
  }
  // 老工作流兼容：未连接输入时，编辑框中已有的内容视为用户编辑
  const textIn = node.inputs?.find(
    (i) => i.name === "text_in" || i.label === "Text Input"
  );
  if (!textIn?.link && !userWidget.value && textWidget.value) {
    userWidget.value = textWidget.value;
  }
}

app.registerExtension({
  name: "OpenAI.NodeExt",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== EDITABLE_TEXT) return;
    // 新建节点：widgets 已就绪时初始化（V3 节点不触发扩展的 nodeCreated 钩子）
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const ret = onNodeCreated?.apply(this, arguments);
      setupEditableText(this);
      return ret;
    };
    // 加载工作流：widget 值恢复后再次确保初始化
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      const ret = onConfigure?.apply(this, arguments);
      setupEditableText(this);
      return ret;
    };
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);
      updateEditableText(this, message);
    };
  },
  // 节点创建（含页面刷新后重建）时初始化隐藏输入与编辑同步
  nodeCreated(node) {
    if (node.type === EDITABLE_TEXT) setupEditableText(node);
  },
  // 缓存输出恢复（页面刷新等）时同步编辑框内容
  onNodeOutputsUpdated(nodeOutputs) {
    for (const [locatorId, output] of Object.entries(nodeOutputs)) {
      const id = Number(locatorId);
      const node = app.rootGraph?.nodes?.find(
        (n) => n.id === id || String(n.id) === locatorId
      );
      if (node?.type === EDITABLE_TEXT) updateEditableText(node, output, false);
    }
  },
});
