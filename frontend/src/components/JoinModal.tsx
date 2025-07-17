import { useMeeting } from "@/hooks/useMeeting";
import { Button, Modal, Space, TextInput } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";


export function JoinModal({ modalOpen, setModalOpen, selectedHashId }: {
  modalOpen: boolean;
  setModalOpen: (open: boolean) => void;
  selectedHashId: string | null;
}) {
  const { t } = useTranslation();
  const { joinMeeting } = useMeeting();
  const [nickname, setNickname] = useState<string>('Participant');

  const handleJoin = () => {
    if (selectedHashId !== null) {
      console.log('用户加入研讨', selectedHashId, nickname);
      setModalOpen(false); // 关闭弹窗
      joinMeeting({ meeting_hash_id: String(selectedHashId), nickname });
    }
  };

  const handleCancel = () => {
    setModalOpen(false);
  };

  return (
    <Modal
      opened={modalOpen}
      onClose={handleCancel}
      title={t('joinDiscussion')}
    >
      <TextInput
        label={t('nickName')}
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
        placeholder={t('nickNamePlaceholder')}
      />
      <Space h="md" />
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="outline" onClick={handleCancel} style={{ marginRight: '10px' }}>
          {t('cancel')}
        </Button>
        <Button onClick={handleJoin}>{t('joinDiscussion')}</Button>
      </div>
    </Modal>
  )
}
