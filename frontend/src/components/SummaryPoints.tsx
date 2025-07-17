import { useState, useCallback } from 'react';
import { RichTextEditor } from '@mantine/tiptap';
import { useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TextAlign from '@tiptap/extension-text-align';
import Superscript from '@tiptap/extension-superscript';
import SubScript from '@tiptap/extension-subscript';
import '@mantine/tiptap/styles.css';
import { useSocket } from '@/lib/socket';
import { Loader, Button, Stack, Group } from '@mantine/core';
import { meetingsManualUpdate } from '@/client';
import { useTranslation } from 'react-i18next';

export function SummaryPoints(props: { meeting_hash_id: string; topic: string }) {
  const { t } = useTranslation();
  const editor = useEditor({
    extensions: [
      // fix list styles in tiptap: revert to default browser styles
      // ref: https://github.com/ueberdosis/tiptap/issues/731#issuecomment-1342360201 
      StarterKit.configure({
        orderedList: { 
          HTMLAttributes: {
            style: 'list-style: revert',
          }
        },
        bulletList: {
          HTMLAttributes: {
            style: 'list-style: revert',
          }
        },
      }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Superscript,
      SubScript,
    ],
    content: '<h1>' + props.topic + '</h1>',
  });

  // 监听来自后端的文本数据
  useSocket("sendSummaryNew", useCallback((data) => {
    const summary = data.summaries;
    console.log('onSendSummaryNew', summary);
    let newContent = '';
    // newContent 的初始值是 editor 的内容

    if (editor) {
      // 1. 保存光标位置
      const { from, to } = editor.state.selection;

      newContent = editor.getHTML();
      newContent += '\n';
      summary.forEach((point) => {
        newContent += '<li>' + point.summary + '\n</li>';
      });

      // 2. 设置富文本编辑器的内容
      editor.commands.setContent(newContent);

      // 3. 恢复光标位置
      editor.commands.setTextSelection({ from, to });
    }
  }, [editor]));

  useSocket("statusAI", useCallback((data) => {
    console.log("onStatusAI", data);
    setRunning(data.running);
  }, []));

  const [running, setRunning] = useState(false);

  return (
    <Stack h='100%' p='xs' gap='xs'>
      <Group justify='space-between'>
        <Button variant='light' size='xs'
          onClick={() => meetingsManualUpdate({ body: { meeting_hash_id: props.meeting_hash_id }})}
        >
          {t('updateDocument')}
        </Button>
        {running && <Loader color="blue" size="sm" />}
      </Group>

      <RichTextEditor editor={editor} style={{ 
        height: '100%',  // 使编辑器占满父容器的高度
        overflowY: 'auto',  // 超过高度时滚动
        // border: '1px solid #ccc',  // 添加边框让编辑器更清晰
        // boxSizing: 'border-box',  // 确保 padding 不会影响高度
      }}>
        <RichTextEditor.Content />
      </RichTextEditor>
    </Stack>
  );
}
