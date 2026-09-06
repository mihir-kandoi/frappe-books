import { createApp } from 'vue';
import { FrappeUI } from 'frappe-ui';
import Badge from 'src/components/Badge.vue';
import { outsideClickDirective } from 'src/utils/outsideClick';
import { fyo } from 'src/initFyo';
import router from 'src/router';
import WebApp from './WebApp.vue';

const app = createApp(WebApp);
app.use(FrappeUI);
app.use(router);
app.component('Badge', Badge);
app.directive('on-outside-click', outsideClickDirective);
app.mixin({
  computed: {
    fyo() {
      return fyo;
    },
    platform() {
      return 'Web';
    },
  },
  methods: { t: fyo.t, T: fyo.T },
});
app.mount('#app');
