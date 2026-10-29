# WSLens 常用任务快捷入口
#
#   make test     —— 运行 44 项单元测试
#   make selftest —— 离线端到端自测
#   make build    —— 一键构建（wheel + 单文件 wslens.pyz）
#   make install  —— 以可编辑模式安装到当前环境
#   make lint     —— 编译期语法检查
#   make clean    —— 清理产物

PYTHON ?= python3

.PHONY: help test selftest build install lint clean demo

help:
	@echo "WSLens 可用任务："
	@echo "  make test      运行单元测试"
	@echo "  make selftest  离线端到端自测"
	@echo "  make demo      启动内置回显服务器（8765 端口）"
	@echo "  make build     一键构建 wheel + wslens.pyz"
	@echo "  make install   本地安装（editable）"
	@echo "  make lint      语法编译检查"
	@echo "  make clean     清理构建产物"

test:
	$(PYTHON) tests/run.py

selftest:
	$(PYTHON) -m wslens selftest

demo:
	$(PYTHON) -m wslens serve --port 8765 --greeting "👋 WSLens 演示服务已就绪" --tick-ms 1000

build:
	bash scripts/build.sh

install:
	$(PYTHON) -m pip install -e .

lint:
	$(PYTHON) -m compileall -q wslens tests

clean:
	rm -rf dist build *.egg-info .pytest_cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
