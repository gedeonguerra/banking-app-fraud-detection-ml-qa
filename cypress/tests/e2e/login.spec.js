import userData from '../../fixtures/user-data.json'
import LoginPage from '../../pages/login.Page'
import HomePage from '../../pages/homePage'

// Instância da página de login para reutilização dos métodos de autenticação
const loginPage = new LoginPage()
// Instância da página inicial para validação do carregamento após login
const homePage = new HomePage()

// FASE 3.4 (correção de fragilidade pré-existente): este spec espera o modal
// de onboarding (usuário sem conta bancária) — nenhum usuário do seed estático
// satisfaz isso hoje (todos já têm conta bancária). Em vez de usuário fixo do
// fixture, cria um usuário NOVO em runtime (cy.createFreshUser(), definido em
// support/commands.ts), que nasce sem conta bancária, satisfazendo o teste.
let freshUser

before(() => {
  cy.createFreshUser().then((user) => {
    freshUser = user
  })
})

// Suite de testes para login bem-sucedido
describe('Login com sucesso RWA teste', () => {
    it('Deve fazer login com um usuário válido', () => {
        // Acessa a página de login
        loginPage.accessLoginPage()
        // Realiza login com o usuário novo criado em runtime
        loginPage.loginWithUser(freshUser.username, freshUser.password)
        // Verifica se a homepage está visível após login
        homePage.checkHomePage()
    })
})

// Suite de testes para login com credenciais inválidas
describe('login com credenciais inválidas', () => {
    it('Deve exibir uma mensagem de erro ao fazer login com credenciais inválidas', () => {
        // Acessa a página de login
        loginPage.accessLoginPage()
        // Tenta login com usuário e senha inválidos
        loginPage.loginWithUser(userData.userFail.username, userData.userFail.password)
        // Verifica se o alerta de erro de login aparece
        loginPage.checkAccessInvalid()
    })
})