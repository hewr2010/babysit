import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MilestoneManageView from '../views/MilestoneManageView.vue'
import PhotoDirectView from '../views/PhotoDirectView.vue'

const routes = [
  {
    path: '/',
    component: HomeView
  },
  {
    path: '/:year/:month',
    component: HomeView
  },
  {
    path: '/milestones/manage',
    component: MilestoneManageView
  },
  {
    path: '/p/:filename',
    component: PhotoDirectView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
