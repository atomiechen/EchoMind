import React, { useEffect, useRef, useState } from 'react';
import { Card, Flex, Text, ScrollArea, Box } from '@mantine/core';
import { IconUserFilled } from '@tabler/icons-react';
import type { AsrSentence, SendAsrData } from '@/lib/models';

interface TransProps {
  trans: SendAsrData;
  setCurrentTime?: (time: number) => void;
  IsEditable?: boolean;
}

const CardList: React.FC<TransProps> = ({ trans, setCurrentTime, IsEditable = false }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [showTooltip, setShowTooltip] = useState<boolean>(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: scrollContainerRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [trans]);

  useEffect(() => {
    let timer: number;
    if (showTooltip) {
      timer = setTimeout(() => setShowTooltip(false), 1000);
    }
    return () => clearTimeout(timer);
  }, [showTooltip]);

  const handleDoubleClick = (card: AsrSentence, index: number) => {
    if (setCurrentTime) {
      const startTime = card.time_range[0] / 1000;
      console.log('handleDoubleClick', startTime);
      setCurrentTime(startTime);
      setSelectedIndex(index);
      setTimeout(() => setSelectedIndex(null), 2000);  // 2秒后取消高亮
    }
  };

  const handleMouseEnter = (event: React.MouseEvent, index: number) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPosition({ top: rect.top - 30, left: rect.left + rect.width / 2 });
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

  return (
    <ScrollArea
      viewportRef={scrollContainerRef}
      type="scroll"
      h="200"
      style={{
        width: '100%',
        flexGrow: 1,
        marginRight: 0,
        marginLeft: 0,
        paddingTop: '2%',
        paddingBottom: '2%',
        wordWrap: 'break-word',
        overflow: 'visible',
      }}
    >
      <Flex direction="column">
        {trans.sentences.map((card, index) => (
          <Card
            key={index}
            style={{
              marginBottom: 10,
              padding: '1px',
              backgroundColor: selectedIndex === index ? '#e0f7fa' : 'white',
              transition: 'background-color 0.3s',
              position: 'relative',
            }}
            onDoubleClick={() => handleDoubleClick(card, index)}
            onMouseEnter={(e) => handleMouseEnter(e, index)}
            onMouseLeave={handleMouseLeave}
          >
            <Flex direction="row">
              <Box style={{ marginLeft: 1, width: '100%' }}>
                <Flex align="center" mb={4} justify="space-between" style={{ width: '100%' }}>
                  <Flex align="center">
                    <IconUserFilled size={16} style={{ marginRight: 4 }} color="#228be6" />
                    <Text size="sm">{trans.speaker[card.speaker_id] || '参会者'}</Text>
                  </Flex>
                  <Text size="xs" color="gray" style={{ marginTop: 4 }} ml="auto">
                    {formatTime(card.time_range[0])} ➔ {formatTime(card.time_range[1])}
                  </Text>
                </Flex>

                <Text size="sm" style={{ marginTop: 0, lineHeight: 1.6 }}>
                  {card.content}
                </Text>
              </Box>
            </Flex>
          </Card>
        ))}
      </Flex>

      {/* 独立的 Tooltip */}
      {showTooltip && IsEditable && (
        <div
          style={{
            position: 'fixed',
            top: tooltipPosition.top,
            left: tooltipPosition.left,
            transform: 'translateX(-50%)',
            backgroundColor: '#f0f0f0',
            padding: '4px 8px',
            borderRadius: '4px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
            zIndex: 9999,
            pointerEvents: 'none',
          }}
        >
          双击跳转对应录音位置
        </div>
      )}
    </ScrollArea>
  );
};

// 格式化时间的辅助函数
const formatTime = (timestamp: number) => {
  const totalSeconds = Math.floor(timestamp / 1000);
  const seconds = totalSeconds % 60;
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const hours = Math.floor(totalSeconds / 3600);

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

export default CardList;
