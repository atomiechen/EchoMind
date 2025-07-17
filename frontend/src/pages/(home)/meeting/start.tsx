import { Button, SegmentedControl, Select, Text, TextInput } from '@mantine/core';
import { TagsInput } from '@mantine/core';
import { useMeeting } from "@/hooks/useMeeting";
import { useTranslation } from "react-i18next";
import { isNotEmpty, useForm } from "@mantine/form";


export function Loader() {
  return {
    header: "startDiscussion",
    documentTitle: "startDiscussion",
  }
}


export default function Start() {
  const { startMeeting } = useMeeting();
  const { t } = useTranslation();

  const form = useForm({
    initialValues: {
      topic: '',
      nickname: 'Participant',
      hotwords: [] as string[],
      meeting_resume_hash_id: '',
      discussionType: 'graph' as 'graph' | 'document',
      meetingLanguage: 'English' as 'English' | 'Chinese',
    },

    validate: {
      topic: isNotEmpty(t('topicErrorEmpty')),
      nickname: isNotEmpty(t('nicknameErrorEmpty')),
    },
  });

  const onSubmit = (values: typeof form.values) => {
    startMeeting({ 
      topic: values.topic, 
      nickname: values.nickname, 
      hotwords: values.hotwords, 
      meeting_resume_hash_id: values.meeting_resume_hash_id, 
      type: values.discussionType, 
      meeting_language: values.meetingLanguage 
    });
  };

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <TextInput label={t('topic')} placeholder={t('topicPlaceholder')}
        withAsterisk
        key={form.key('topic')}
        {...form.getInputProps('topic')}
      />
      <TextInput label={t('nickName')} placeholder={t('nickNamePlaceholder')} mt="md"
        withAsterisk
        key={form.key('nickname')}
        {...form.getInputProps('nickname')}
      />
      <Select
        mt="md"
        label={t('discussionLanguage')}
        data={[
          { value: 'English', label: 'English' },
          { value: 'Chinese', label: '中文' },
        ]}
        allowDeselect={false}
        withAsterisk
        key={form.key('meetingLanguage')}
        {...form.getInputProps('meetingLanguage')}
      />
      <TagsInput
        mt="md"
        data={[]}
        label={t('hotwords')}
        placeholder={t('hotwordsHelp')}
        splitChars={[',', '|']}
        clearable
        key={form.key('hotwords')}
        {...form.getInputProps('hotwords')}
      />
      <TextInput
        label={t('resumeMeetingHashId')}
        placeholder={t('resumeMeetingHashIdPlaceholder')}
        mt="md"
        key={form.key('meeting_resume_hash_id')}
        {...form.getInputProps('meeting_resume_hash_id')}
      />

      <Text size="sm" fw={500} mt="md">
        {t('supportSystem')}
      </Text>
      <SegmentedControl
        color='blue'
        data={[{label: 'EchoMind', value: 'graph'}, {label: 'AutoDoc', value: 'document'}]}
        key={form.key('discussionType')}
        {...form.getInputProps('discussionType')}
      />

      <Button
        variant="light"
        color="blue"
        fullWidth
        mt='20'
        type='submit'
      >{t('startDiscussion')}</Button>
    </form>
  );
};
