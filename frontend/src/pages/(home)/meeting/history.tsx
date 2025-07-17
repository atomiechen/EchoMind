import { Button, Space, Badge, Table, Loader as LoaderComp, Input, InputWrapper, Tooltip, Pagination, Stack, Group } from '@mantine/core';
import { useRef, useState, type KeyboardEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { error } from "@/lib/notifications";
import { type MeetingItem } from '@/client';
import { queryClient } from '@/lib/query';
import { useSuspenseQuery } from '@tanstack/react-query';
import { meetingsGetAllMeetingsOptions } from '@/client/@tanstack/react-query.gen';
import { useValueChange } from '@/hooks/useValueChange';
import { useTranslation } from 'react-i18next';
import { IconSearch } from '@tabler/icons-react';
import { formatDateTime } from '@/lib/utils';
import { JoinModal } from '@/components/JoinModal';


export async function Loader() {
  return {
    header: "discussionHistory",
    documentTitle: "discussionHistory",
  }
}


/**
 * Show loading UI while the main component is being loaded
 */
export const Pending = () => <LoaderComp />;


const PAGE_SIZE = 20;

export default function History() {
  const { t } = useTranslation();

  const [searchParams, setSearchParams] = useSearchParams();
  const initialPage = parseInt(searchParams.get("p") || '1');
  const initialSearch = searchParams.get("q") || '';

  const { data: meetingList } = useSuspenseQuery({
    ...meetingsGetAllMeetingsOptions({
      query: {
        title: initialSearch,
        limit: PAGE_SIZE,
        offset: (initialPage - 1) * PAGE_SIZE,
      }
    }),
    staleTime: 30 * 1000,  // 30 seconds
  });

  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(meetingList.total);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const [page, setPage] = useState(initialPage);  // 当前页码
  const [searchValue, setSearchValue] = useState(initialSearch);  // 搜索框的值

  const [dataSource, setDataSource] = useState<MeetingItem[]>(meetingList.meetings);
  useValueChange((newMeetingList) => {
    setDataSource(newMeetingList.meetings);
  }, meetingList);

  const inputRef = useRef<HTMLInputElement>(null);

  const onSearch = (value: string, page: number) => {
    console.log("Searching for meetings with title:", value, "on page:", page);
    setLoading(true);
    queryClient.fetchQuery(meetingsGetAllMeetingsOptions({
      query: {
        // hash_id: params?.hash_id,
        title: value,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }
    }))
    .then((res) => {
        setDataSource(res.meetings);
        setTotal(res.total);
    })
    .catch((err) => {
      console.log("Unknown error fetching discussions:", String(err.detail));
      error(t('searchError'), err.detail);
    })
    .finally(() => {
      setLoading(false);
    });
  }

  const handlePageChange = (newPage: number) => {
    if (newPage === page) return;  // 如果页码没有变化，直接返回
    setPage(newPage);
    setSearchParams(Object.entries({ p: newPage.toString(), q: searchValue }).filter(([_, v]) => v));  // 记录在 URL 里
    if (inputRef.current) {
      inputRef.current.value = searchValue;  // 恢复搜索框的值，如果被临时更改
    }
    onSearch?.(searchValue, newPage);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setPage(1);
      const value = (e.target as HTMLInputElement).value;
      setSearchValue(value);
      setSearchParams(Object.entries({ p: '1', q: value }).filter(([_, v]) => v));  // 记录在 URL 里
      onSearch?.(value, 1);  // reset to first page on new search
    }
  };

  // 控制弹窗状态和当前选中会议的 hash_id
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedHashId, setSelectedHashId] = useState<string | null>(null);

  return (
    <div>
      <InputWrapper required p='sm'>
        <Input
          placeholder={t('search')}
          onKeyDown={handleKeyDown}
          // value={searchValue}
          // onChange={(e) => setSearchValue(e.target.value)}
          defaultValue={searchValue}
          leftSection={<IconSearch size={18} />}
          ref={inputRef}
        />
      </InputWrapper>
      {loading ? (
        <LoaderComp />
      ) : (
        (
          <>
            <Stack pb='md'>
              <Table striped highlightOnHover stickyHeader stickyHeaderOffset={45}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th style={{ textAlign: 'center' }}>{t('meetingHashId')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('createdAt')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('createdBy')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('topic')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('status')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('host')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('language')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('hotwords')}</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>{t('action')}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                {dataSource.map((item) => {
                  const { formattedDate, formattedTime } = formatDateTime(item.create_time);
                  return (
                    <Table.Tr key={item.id}>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <Tooltip label={item.hash_id}>
                          <span>{item.hash_id}</span>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', padding: '8px', borderRight: '1px solid #ccc' }}>
                        <div>{formattedDate}</div>
                        <div>{formattedTime}</div>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>{item.create_by}</Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <Tooltip label={item.topic}>
                          <span>{item.topic}</span>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <Space>
                          <Badge color={item.status === 'processing' ? 'blue' : 'gray'}>
                            {item.status === 'processing' ? t('statusOngoing') : t('statusFinished')}
                          </Badge>
                        </Space>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <Tooltip label={item.master}>
                          <span>{item.master}</span>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <span>{item.meeting_language === 'English' ? 'English' : '中文'}</span>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', borderRight: '1px solid #ccc', padding: '8px' }}>
                        <Tooltip label={item.hotwords}>
                          <span>{item.hotwords}</span>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', padding: '8px' }}>
                      <Space>
                        {item.status === 'finished' ? (
                          <Link to={`/record/${item.id}`}>{t('detail')}</Link>
                        ) : (
                          <>
                            <Button onClick={() => {
                              setSelectedHashId(item.hash_id);
                              setModalOpen(true);
                            }}>{t('joinDiscussion')}</Button>
                          </>
                        )}
                      </Space>
                    </Table.Td>
                    </Table.Tr>
                );
              })}
                </Table.Tbody>
              </Table>
              <Pagination.Root total={totalPages} value={page} onChange={handlePageChange}>
                <Group gap={5} justify="center">
                  <Pagination.Previous />
                  <Pagination.Items />
                  <Pagination.Next />
                </Group>
              </Pagination.Root>
            </Stack>
            <JoinModal
              modalOpen={modalOpen}
              setModalOpen={setModalOpen}
              selectedHashId={selectedHashId}
            />
          </>
        )
      )}
    </div>
  )
}
