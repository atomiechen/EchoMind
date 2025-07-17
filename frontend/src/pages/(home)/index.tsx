import { meetingsGetOngoingMeetingsOptions } from '@/client/@tanstack/react-query.gen';
import { JoinModal } from '@/components/JoinModal';
import { formatedDateTimeString } from '@/lib/utils';
import { Button, Card, SimpleGrid, Stack, Text, Loader as LoaderComp } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';


export function Loader() {
  return {
    header: "home",
    documentTitle: "home",
  }
}


const shortCuts = [
  { key: 'startDiscussion', link: '/meeting/start' },
  { key: 'joinDiscussion', link: '/meeting/join' },
  { key: 'discussionHistory', link: '/meeting/history' },
]

const recentCount = 3;
export default function Index() {
  const { t } = useTranslation();

  const { data: ongoingMeetings, isLoading } = useQuery({
    ...meetingsGetOngoingMeetingsOptions({ query: { limit: recentCount } }),
    staleTime: 30 * 1000,  // 30 seconds
  })

  // 控制弹窗状态和当前选中会议的 hash_id
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedHashId, setSelectedHashId] = useState<string | null>(null);

  return (
    <Stack h='100%' align='center' justify='center' gap='xl'>
      <Text
        size="xl"
        fw={900}
        variant="gradient"
        gradient={{ from: 'blue', to: 'cyan', deg: 90 }}
      >
        {t('welcome')}
      </Text>
      <SimpleGrid cols={shortCuts.length} spacing="lg">
        {shortCuts.map((item) => (
          <Link to={item.link} key={item.key}>
            <Button size='sm' radius='md' variant='light'>
              {t(item.key as never)}
            </Button>
          </Link>
        ))}
      </SimpleGrid>
      <Stack m='xl' align='center'>
        {isLoading 
          ? <LoaderComp />
          :
          <>
            {ongoingMeetings?.meetings && ongoingMeetings.meetings.length > 0 && <Text size='md' c='dimmed'>{t('ongoingTitle')}</Text>}
            <SimpleGrid cols={3} spacing="lg">
              {ongoingMeetings?.meetings.map((meeting) => (
                <Card withBorder shadow="sm" radius="md" key={meeting.hash_id}>
                  <Text fw={500}>{meeting.topic}</Text>
                  <Text size="sm" c="dimmed">
                    {meeting.create_by}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {formatedDateTimeString(meeting.create_time)}
                  </Text>
                  <Button color="blue" fullWidth mt="md" radius="md" onClick={() => {
                    setSelectedHashId(meeting.hash_id);
                    setModalOpen(true);
                  }}>
                    {t('joinDiscussion')}
                  </Button>
                </Card>
              ))}
            </SimpleGrid>
          </>
        }
      </Stack>
      <JoinModal
        modalOpen={modalOpen}
        setModalOpen={setModalOpen}
        selectedHashId={selectedHashId}
      />
    </Stack>
  );
}
