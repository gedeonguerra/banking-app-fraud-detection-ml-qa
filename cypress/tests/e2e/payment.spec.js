import LoginPage from '../../pages/login.Page'
import Payment from '../../pages/payment.Page'

// Instância da página de login para realizar autenticação
const loginPage = new LoginPage()
// Instância da página de pagamento para executar fluxos de transação
const payment = new Payment()

// FASE 3.4 (correção de fragilidade pré-existente): paymentWithSuccess()
// executa o fluxo de onboarding bancário (pendente), e paymentWithfail() já
// assume que o onboarding foi concluído — por isso os dois describes abaixo
// PRECISAM do MESMO usuário (mesmo comportamento de antes, quando os dois
// usavam o mesmo userData.userSucess estático). Agora criado uma única vez
// em runtime via cy.createFreshUser(), nascendo sem conta bancária.
let freshUser

before(() => {
  cy.createFreshUser().then((user) => {
    freshUser = user
  })
})

// Suite de testes para envio de dinheiro com saldo suficiente
describe('Enviar dinheiro com saldo suficiente', () => {
    it('Deve enviar dinheiro com sucesso', () => {
        // Acessa a página de login
        loginPage.accessLoginPage()
        // Realiza login com o usuário novo criado em runtime
        loginPage.loginWithUser(freshUser.username, freshUser.password)

        // Executa o fluxo completo de pagamento bem-sucedido (inclui onboarding)
        payment.paymentWithSuccess()
        // Verifica se a confirmação do pagamento foi exibida
        payment.checkPayment()
    })
})

// Suite de testes para envio de dinheiro com saldo insuficiente
describe('Enviar dinheiro com saldo insuficiente', () => {
    it('Deve exibir mensagem de erro ao enviar dinheiro sem saldo suficiente', () => {
        // Acessa a página de login
        loginPage.accessLoginPage()
        // Realiza login com o MESMO usuário criado acima (onboarding já concluído)
        loginPage.loginWithUser(freshUser.username, freshUser.password)

        // Executa o fluxo que tenta pagamento e deve falhar (sem etapas de onboarding)
        payment.paymentWithfail()
        // Verifica se a mensagem de erro ou confirmação adequada aparece
        payment.checkPayment()
    })
})