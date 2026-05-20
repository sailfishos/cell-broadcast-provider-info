TEMPLATE = aux

ATTENTION_TONE_DIR = $$OUT_PWD/attention-tones
ATTENTION_TONES = $$ATTENTION_TONE_DIR/cellbroadcast-attention-853-960.ogg

attentiontones.target = attentiontones
attentiontones.commands = $$QMAKE_MKDIR $$shell_quote($$ATTENTION_TONE_DIR) && python3 $$shell_quote($$PWD/tools/generate-cellbroadcast-attention-tones.py) --output-dir $$shell_quote($$ATTENTION_TONE_DIR)

first.depends = attentiontones
QMAKE_EXTRA_TARGETS += attentiontones first

channels.files = data/channels.json
channels.path = /usr/share/cell-broadcast-provider-info

attentiontonefiles.files = $$ATTENTION_TONES
attentiontonefiles.path = /usr/share/cell-broadcast-provider-info/attention-tones
attentiontonefiles.CONFIG += no_check_exist

pkgconfig.files = cell-broadcast-provider-info.pc
pkgconfig.path = /usr/share/pkgconfig

INSTALLS += channels attentiontonefiles pkgconfig

OTHER_FILES += README.md LICENSE rpm/*.spec tools/*.py
