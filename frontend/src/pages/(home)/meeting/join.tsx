import { Button, TextInput } from '@mantine/core';
import { useMeeting } from "@/hooks/useMeeting";
import { isNotEmpty, useForm } from "@mantine/form";
import { useTranslation } from "react-i18next";


export function Loader() {
  return {
    header: "joinDiscussion",
    documentTitle: "joinDiscussion",
  }
}


export default function Join() {
  const { joinMeeting } = useMeeting();
  const { t } = useTranslation();

  const form = useForm({
    initialValues: {
      meeting_hash_id: '',
      nickname: 'Participant',
    },

    validate: {
      meeting_hash_id: isNotEmpty(t('meetingHashIdErrorEmpty')),
      nickname: isNotEmpty(t('nicknameErrorEmpty')),
    },
  });

  const onSubmit = (values: typeof form.values) => {
    joinMeeting({
      meeting_hash_id: values.meeting_hash_id,
      nickname: values.nickname,
    })
  };

  return (
    <form onSubmit={form.onSubmit(onSubmit)}>
      <TextInput label={t('meetingHashId')} placeholder={t('meetingHashId')} 
        withAsterisk
        key={form.key('meeting_hash_id')}
        {...form.getInputProps('meeting_hash_id')}
      />
      <TextInput label={t('nickName')} placeholder={t('nickName')} mt="md" 
        withAsterisk
        key={form.key('nickname')}
        {...form.getInputProps('nickname')}
      />
      <Button fullWidth mt='20' type="submit">{t('joinDiscussion')}</Button>
    </form>
  );
};
