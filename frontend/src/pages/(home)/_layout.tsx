import { Outlet, redirect, useLoaderData, useMatches, useNavigate } from "react-router";
import { AppShell, Burger, Group, ScrollArea, Stack, useMantineTheme, Badge, Code, Text, Center, Button } from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import { useCallback, useMemo, useState } from "react";
import { Navbar } from '@/components/NavBar/NavBar';
import type { NavItem } from "@/lib/definitions";
import { IconArrowsJoin2, IconHome, IconList, IconLogout, IconSquareRoundedPlus } from "@tabler/icons-react";
import { SideResizable } from "@/components/SideResizable/SideResizable";
import { socket, useSocket } from "@/lib/socket";
import { usersCheckLogin, usersLogout } from "@/client";
import { useMeeting } from "@/hooks/useMeeting";
import { useMeetingStore } from "@/store/meetingStore";
import { LanguagePicker } from "@/components/LanguagePicker";
import { useTranslation } from "react-i18next";
import { useShallow } from "zustand/react/shallow";


export async function Loader() {
  try {
    // return 'changethis'; // TODO: remove this line
    const res = await usersCheckLogin();
    if (res.data.code === 0) {
      socket.connect();
      return res.data.username;
    } else {
      socket.disconnect();
      return redirect('/login');
    }
  } catch (err) {
    console.error(err);
    socket.disconnect();
    return redirect('/login');
  }
}


export default function BaseLayout() {
  const [isConnected, setIsConnected] = useState<boolean>(socket.connected);
  if (socket.connected !== isConnected) {
    setIsConnected(socket.connected);
  }

  const [mobileOpened, toggleMobile, closeMobile, desktopOpened, toggleDesktop] = useMeetingStore(
    useShallow((s) => [s.mobileOpened, s.toggleMobile, s.closeMobile, s.desktopOpened, s.toggleDesktop]),
  );

  const [navbarWidth, setNavbarWidth] = useState<number>(250);
  const username = useLoaderData<typeof Loader>();
	const navigate = useNavigate();
  const { leaveMeeting } = useMeeting();
  const headerContent = useMeetingStore((s) => (s.headerContent));

  const theme = useMantineTheme();
  const isMobile = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);

  const { t } = useTranslation();

  const matches = useMatches();
  const lastMatch = matches[matches.length - 1]; // the last match is the current route
  const { header, documentTitle } = (lastMatch?.data as { header?: string; documentTitle?: string }) ?? {};
  const realHeader = header ? t(header as never) : headerContent;
  if (documentTitle) {
    document.title = "EchoMind " + t(documentTitle as never);
  } else {
    document.title = "EchoMind";
  }


  const navItems: NavItem[] = useMemo(() => [
    { link: '/', label: t('home'), icon: IconHome },
    { link: '/meeting/start', label: t('startDiscussion'), icon: IconSquareRoundedPlus },
    { link: '/meeting/join', label: t('joinDiscussion'), icon: IconArrowsJoin2 },
    { link: '/meeting/history', label: t('discussionHistory'), icon: IconList },
  ], [t]);

  useSocket("connect", useCallback(() => {
    setIsConnected(true);
  }, []));

  useSocket("disconnect", useCallback(() => {
    setIsConnected(false);
  }, []));

  return (
    <AppShell
      header={{ height: 50 }}
      navbar={{
        width: navbarWidth,
        breakpoint: 'sm',
        collapsed: { mobile: !mobileOpened, desktop: !desktopOpened },
      }}
      padding="md"
      // layout="alt"
      styles={{
        main: {
          height: '100dvh',
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="sm" size="sm" />
            <Burger onClick={toggleDesktop} visibleFrom="sm" size="sm" />
            {realHeader}
          </Group>
          <Group>
            <Badge size='md' color={isConnected ? 'blue' : 'red'} >
              {isConnected ? t('connected') : t('disconnected')}
            </Badge>
            <LanguagePicker />
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar>
        <Stack gap={0} p='md' h='100%'
          // render if not mobile to allow resizing
          renderRoot={isMobile ? undefined : (props) => (
            <SideResizable 
              defaultSize={{
                height: '100%',
              }}
              onResize={(e, direction, ref, d) => {
                setNavbarWidth(ref.offsetWidth);
              }}
              minWidth={250}
              maxWidth={500}
              side='right'
              enabled={desktopOpened}
              {...props}
            />
          )}
        >
          <AppShell.Section>
            <Group py="md">
              <Stack justify="space-between" >
                <Text
                  size="lg"
                  fw={900}
                  variant="gradient"
                  gradient={{ from: 'blue', to: 'cyan', deg: 90 }}
                >
                  EchoMind
                </Text>
                <Group ml="xl">
                  <Text size='md' c={'gray'}>{t('user')}</Text>
                  <Code fw={700}>{username}</Code>
                </Group>
                <Group ml="xl">
                  <Text size='md' c={'gray'}>Socket</Text>
                  <Badge size='md' color={isConnected ? 'blue' : 'red'} >
                    {isConnected ? t('connected') : t('disconnected')}
                  </Badge>
                </Group>
              </Stack>
            </Group>
          </AppShell.Section>
          
          <AppShell.Section grow my="md" component={ScrollArea} type='scroll'>
            <Navbar data={navItems} clickHandler={closeMobile} />
          </AppShell.Section>

          <AppShell.Section>
            <Center>
              <Button 
                variant="subtle" color='gray'
                fullWidth  
                leftSection={<IconLogout />}
                onClick={
                  () => {
                    socket.disconnect();
                    leaveMeeting();  // ensure leaving meeting on logout
                    usersLogout().then((res) => {
                      console.log(res);
                      if (res.data.code === 0) {
                          navigate('/login');
                      }
                    }).catch((err) => {
                      console.error(err);
                      navigate('/login');
                    });
                  }
                }
              >{t('actionLogout')}</Button>
            </Center>
          </AppShell.Section>

        </Stack>
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
