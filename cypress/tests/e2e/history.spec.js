import userData from '../../fixtures/user-data.json'
import LoginPage from '../../pages/login.Page'
import HitoryPage from '../../pages/transaction-historyPage'

// Instância da página de login para reutilizar métodos de login
const loginPage = new LoginPage()
// Instância da página de histórico para acessar os métodos de visualização
const history = new HitoryPage()

// FASE 3.4 (correção de fragilidade pré-existente, ajuste 2): os dois
// describes abaixo precisam de usuários DIFERENTES, não do mesmo:
// - "com sucesso" clica num ID de transação hardcoded (6XY0Ud1i8sp4),
//   confirmado real, entre Dina20 (senderId) e Judah_Dietrich50 (receiverId).
//   Além disso, precisa de conta bancária (senão o modal de onboarding cobre
//   a tela e bloqueia o clique) — por isso usa userWithHistory (Dina20),
//   fixo no fixture, não um usuário novo.
// - "sem transações anteriores" precisa de um usuário genuinamente sem
//   histórico — mantém cy.createFreshUser(), já validado funcionando.

describe('Visualizar histórico de transações com sucesso', () => {
    it('Deve exibir o histórico de transações de um usuário corretamente', () => {
        // Acessa a página de login
        loginPage.accessLoginPage()
        // Realiza login com usuário real que tem a transação pública esperada pelo teste
        loginPage.loginWithUser(userData.userWithHistory.username, userData.userWithHistory.password)

        // Executa o fluxo de visualização bem-sucedida do histórico
        history.successfulViewing()
    })
})

describe('Tentar visualizar o histórico de transações sem transações anteriores', () => {
    it('Deve exibir uma mensagem indicando que o usuário não possui transações anteriores', () => {
        cy.createFreshUser().then((user) => {
            // Acessa a página de login
            loginPage.accessLoginPage()
            // Realiza login com usuário novo, sem histórico nenhum
            loginPage.loginWithUser(user.username, user.password)

            // Executa o fluxo que tenta visualizar o histórico e espera falha (sem transações)
            history.failedViewing()
        })
    })
})