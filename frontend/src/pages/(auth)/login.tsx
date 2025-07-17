import {
  TextInput,
  PasswordInput,
  Anchor,
  Paper,
  Title,
  Text,
  Container,
  Group,
  Button,
  Affix,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { redirect, useNavigate } from 'react-router';
import { useToggle } from '@mantine/hooks';
import { showLoading, updateError, updateSuccess } from '@/lib/notifications';
import { usersCheckLogin, usersLogin, usersRegister } from '@/client';
import { LanguagePicker } from '@/components/LanguagePicker';
import { useTranslation } from 'react-i18next';

export async function Loader() {
  try {
    const res = await usersCheckLogin();
    if (res.data.code === 0) {
      return redirect('/');
    }
  } catch (err) {
    console.error(err);
  }
}

export default function Login() {
  const navigate = useNavigate();
  const [type, toggle] = useToggle(['login', 'register']);

  const { t } = useTranslation();

  document.title = "EchoMind - Login";

  const form = useForm({
    initialValues: {
      username: '',
      password: '',
    },

    validate: {
      username: (val) => (val.trim().length >= 2 ? null : 'Username should have at least 2 characters'),
      password: (val) => (val.length >= 4 ? null : 'Password should have at least 4 characters'),
    },
  });

  const onSubmit = (values: typeof form.values) => {
    const id = showLoading('Logging in...');
    usersLogin({ body: { username: values.username, password: values.password } }).then((res) => {
      if (res.data.code === 0) {
        updateSuccess(id, 'Login successful');
        navigate('/');
      } else {
        console.log(res.data);
        updateError(id, 'Login failed', 'Check your username and password');
      }
    }).catch((err) => {
      console.log(err);
      updateError(id, 'Login failed', 'Network error');
    });
  };

  const onRegister = (values: typeof form.values) => {
    const id = showLoading('Registering...');
    usersRegister({ body: { username: values.username, password: values.password } }).then((res) => {
        if (res.data.code === 0) {
          updateSuccess(id, 'Registration successful');
          // navigate('/');
          toggle(); // Switch to login
        } else {
          console.log(res.data);
            if (res.data.code === 10) {
              updateError(id, 'Registration failed', 'Username already exists');
            } else {
              updateError(id, 'Registration failed', 'Password does not meet requirements');
            }
        }
    }).catch((err) => {
      console.log(err);
      updateError(id, 'Registration failed', 'Network error');
    });
  }

  return (
    <>
      <Container my={'14vh'} maw={450}>
        <Title ta="center" >
          {type === 'register' ? t('registration') : t('login')}
        </Title>
        <Text c="dimmed" size="md" ta="center" mt={5}>
          EchoMind
          {/* <Anchor size="sm" component="button">
          Create account
        </Anchor> */}
        </Text>

        <Paper withBorder shadow="md" p={30} mt={30} radius="md">

        <form onSubmit={
          type === 'register' ? form.onSubmit(onRegister) : form.onSubmit(onSubmit)
        }>

          <TextInput 
            label={t('username')} placeholder={t('username')}
            key={form.key('username')}
            {...form.getInputProps('username')}
          />
          <PasswordInput 
            label={t('password')} placeholder={t('password')} mt="md" 
            key={form.key('password')}
            {...form.getInputProps('password')}
          />
          <Group justify="space-between" mt="lg">
            <Anchor component="button" type="button" size="sm" onClick={() => toggle()}>
              {type === 'register'
                ? t('haveAccount')
                : t('noAccount')}
            </Anchor>
          </Group>
          <Button fullWidth mt="xl" type="submit"
            color={type === 'register' ? 'teal' : 'blue'}
          >
            {type === 'register' ? t('actionRegister') : t('actionLogin')}
          </Button>
        </form>
        </Paper>
      </Container>
      <Affix position={{ top: 20, right: 20 }}>
        <LanguagePicker />
      </Affix>
    </>
  );
}
